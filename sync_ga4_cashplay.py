"""
캐시플레이 GA4 자동 적재 스크립트 (Supabase 버전)
- GA4에서 전일자 데이터를 조회하여 Supabase에 upsert
- 쿼리 분리:
    cashplay_ga      → 이벤트/페이지 차원 + 이벤트 지표
    cashplay_ga_user → date 차원만 + 사용자 지표 (DAU/WAU/MAU 정확한 값)
- GitHub Actions에서 매일 오전 9시(KST) 실행
"""

import os
import sys
import json
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
from urllib.parse import urlparse

from supabase import create_client
from google.oauth2.service_account import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    FilterExpression,
    Filter,
)

# ============================================================
# 설정
# ============================================================
TABLE_EVENT = "cashplay_ga"
TABLE_USER  = "cashplay_ga_user"
INTERNAL_DOMAIN = "app.cashplay.io"
DEFAULT_DAYS = 7

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def get_ga4_client():
    creds_json = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    return BetaAnalyticsDataClient(credentials=creds)


def get_supabase_client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def _stream_filter():
    return FilterExpression(
        filter=Filter(
            field_name="streamName",
            string_filter=Filter.StringFilter(
                match_type=Filter.StringFilter.MatchType.EXACT,
                value="캐시플레이",
            ),
        )
    )


def _parse_rows(headers: list, response_rows) -> list:
    """GA4 응답 rows → list[dict] 변환"""
    rows = []
    for row in response_rows:
        row_data = {}
        for i, dim_value in enumerate(row.dimension_values):
            val = dim_value.value
            col = headers[i]
            if col == "date" and len(val) == 8 and val.isdigit():
                val = f"{val[:4]}-{val[4:6]}-{val[6:]}"
            if col == "pageReferrer" and val:
                try:
                    parsed = urlparse(val)
                    if parsed.hostname and INTERNAL_DOMAIN in parsed.hostname:
                        val = parsed.path or "/"
                    elif parsed.hostname:
                        val = "(external)"
                except Exception:
                    pass
            row_data[col] = val
        for i, metric_value in enumerate(row.metric_values):
            col = headers[len(row.dimension_values) + i]
            val = float(metric_value.value)
            if col == "engagementRate":
                val = round(val * 100, 2)
            row_data[col] = val
        rows.append(row_data)
    return rows


def _sanitize_col(name: str) -> str:
    """GA4 컬럼명을 Supabase 컬럼명으로 변환 (customEvent:xxx → xxx)"""
    if name.startswith("customEvent:"):
        return name.split(":", 1)[1]
    return name


def fetch_ga4_event_data(property_id: str, start_date: str, end_date: str) -> list:
    client = get_ga4_client()

    dimensions = [
        Dimension(name="date"),
        Dimension(name="eventName"),
        Dimension(name="pageTitle"),
        Dimension(name="pagePath"),
        Dimension(name="customEvent:page"),
        Dimension(name="customEvent:page_type"),
        Dimension(name="customEvent:button_id"),
    ]
    metrics = [
        Metric(name="eventCount"),
        Metric(name="sessions"),
        Metric(name="screenPageViews"),
        Metric(name="averageSessionDuration"),
        Metric(name="engagementRate"),
        Metric(name="userEngagementDuration"),
    ]

    raw_headers = [d.name for d in dimensions] + [m.name for m in metrics]
    db_headers  = [_sanitize_col(h) for h in raw_headers]

    request = RunReportRequest(
        property=property_id,
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimension_filter=_stream_filter(),
        dimensions=dimensions,
        metrics=metrics,
        limit=100000,
    )

    rows = []
    offset = 0
    while True:
        request.offset = offset
        request.limit = 100000
        response = client.run_report(request)
        raw_rows = _parse_rows(raw_headers, response.rows)
        for row in raw_rows:
            converted = {new: row.get(orig) for orig, new in zip(raw_headers, db_headers)}
            rows.append(converted)
        offset += len(response.rows)
        print(f"[sync] {TABLE_EVENT} 조회 중: {offset} / {response.row_count}행")
        if offset >= response.row_count:
            break

    return rows


def fetch_ga4_user_data(property_id: str, start_date: str, end_date: str) -> list:
    client = get_ga4_client()

    dimensions = [Dimension(name="date")]
    metrics = [
        Metric(name="activeUsers"),
        Metric(name="active7DayUsers"),
        Metric(name="active28DayUsers"),
        Metric(name="newUsers"),
        Metric(name="sessions"),
    ]
    raw_headers = [d.name for d in dimensions] + [m.name for m in metrics]

    request = RunReportRequest(
        property=property_id,
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimension_filter=_stream_filter(),
        dimensions=dimensions,
        metrics=metrics,
        limit=100000,
    )

    rows = []
    offset = 0
    while True:
        request.offset = offset
        request.limit = 100000
        response = client.run_report(request)
        rows.extend(_parse_rows(raw_headers, response.rows))
        offset += len(response.rows)
        print(f"[sync] {TABLE_USER} 조회 중: {offset} / {response.row_count}행")
        if offset >= response.row_count:
            break

    return rows


def upsert_event_data(client, rows: list, days: int):
    """이벤트 데이터를 날짜 기준으로 삭제 후 재삽입"""
    if not rows:
        print("[sync] 삽입할 이벤트 데이터 없음")
        return 0

    dates = {row["date"] for row in rows if row.get("date")}
    for d in dates:
        client.table(TABLE_EVENT).delete().eq("date", d).execute()
    print(f"[sync] {TABLE_EVENT} {len(dates)}개 날짜 기존 데이터 삭제 완료")

    chunk_size = 1000
    total = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        client.table(TABLE_EVENT).insert(chunk).execute()
        total += len(chunk)

    print(f"[sync] {TABLE_EVENT}에 {total}행 적재 완료")
    return total


def upsert_user_data(client, rows: list):
    """사용자 데이터 upsert (date PRIMARY KEY)"""
    if not rows:
        print("[sync] 삽입할 사용자 데이터 없음")
        return 0

    chunk_size = 1000
    total = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        client.table(TABLE_USER).upsert(chunk, on_conflict="date").execute()
        total += len(chunk)

    print(f"[sync] {TABLE_USER}에 {total}행 적재 완료")
    return total


def main():
    property_id = os.environ.get("GA4_CASHPLAY_PROPERTY_ID")

    if not property_id:
        print("[ERROR] GA4_CASHPLAY_PROPERTY_ID 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    days = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DAYS

    end_date = datetime.now(KST) - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"[sync] 캐시플레이 GA4 데이터 수집")
    print(f"[sync] 기간: {start_str} ~ {end_str} ({days}일)")
    print(f"[sync] Property ID: {property_id}")

    client = get_supabase_client()

    # ── 이벤트 데이터 → cashplay_ga ──
    event_rows = fetch_ga4_event_data(property_id, start_str, end_str)
    if event_rows:
        print(f"[sync] 이벤트 데이터 {len(event_rows)}행 조회 완료")
        upsert_event_data(client, event_rows, days)
    else:
        print("[sync] 이벤트 데이터 없음")

    # ── 사용자 데이터 → cashplay_ga_user ──
    user_rows = fetch_ga4_user_data(property_id, start_str, end_str)
    if user_rows:
        print(f"[sync] 사용자 데이터 {len(user_rows)}행 조회 완료")
        upsert_user_data(client, user_rows)
    else:
        print("[sync] 사용자 데이터 없음")


if __name__ == "__main__":
    main()
