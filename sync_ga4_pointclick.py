"""
포인트클릭_GA / 포인트클릭_GA_USER 시트 자동 적재 스크립트
- GA4에서 전일자 데이터를 조회하여 Google Sheets에 덮어쓰기
- 쿼리 분리:
    포인트클릭_GA      → 이벤트/페이지 차원 + 이벤트 지표 (eventCount, sessions 등)
    포인트클릭_GA_USER → date 차원만 + 사용자 지표 (DAU/WAU/MAU 정확한 값)
- GitHub Actions에서 매일 오전 9시(KST) 실행
"""

import os
import json
import sys
from datetime import datetime, timedelta
from urllib.parse import urlparse

import gspread
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
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SHEET_NAME_EVENT = "포인트클릭_GA"       # 이벤트/페이지 데이터
SHEET_NAME_USER  = "포인트클릭_GA_USER"  # 사용자 지표 (DAU/WAU/MAU)
INTERNAL_DOMAIN = "ad.pointclick.co.kr"
MEDIA_MASTER_SHEET = "매체마스터"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/analytics.readonly"
]

# GA4 수집 기간 (최근 N일)
DEFAULT_DAYS = 7


def get_gspread_client():
    """Google Sheets 클라이언트 생성"""
    creds_json = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    return gspread.authorize(creds)


def get_ga4_client():
    """GA4 클라이언트 생성"""
    creds_json = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    return BetaAnalyticsDataClient(credentials=creds)


def load_media_master():
    """매체 마스터 데이터 로드"""
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.worksheet(MEDIA_MASTER_SHEET)
        data = ws.get_all_values()

        if not data or len(data) < 2:
            print("[warn] 매체 마스터 시트가 비어있습니다.")
            return {}

        headers = data[0]
        media_key_idx = None
        media_name_idx = None

        for i, h in enumerate(headers):
            if h == '매체키' or h == 'media_key':
                media_key_idx = i
            if h == '매체명' or h == 'media_name':
                media_name_idx = i

        if media_key_idx is None or media_name_idx is None:
            print("[warn] 매체 마스터에 필수 컬럼(매체키, 매체명)이 없습니다.")
            return {}

        media_dict = {}
        for row in data[1:]:
            if len(row) > max(media_key_idx, media_name_idx):
                key = row[media_key_idx]
                name = row[media_name_idx]
                if key and name:
                    media_dict[key] = name

        print(f"[sync] 매체 마스터 {len(media_dict)}개 로드 완료")
        return media_dict

    except Exception as e:
        print(f"[warn] 매체 마스터 로드 실패: {str(e)}")
        return {}


def _stream_filter():
    """포인트클릭 스트림 필터 공통"""
    return FilterExpression(
        filter=Filter(
            field_name="streamName",
            string_filter=Filter.StringFilter(
                match_type=Filter.StringFilter.MatchType.EXACT,
                value="포인트클릭 - 운영 환경",
            ),
        )
    )


def _parse_rows(headers, response_rows):
    """GA4 응답 rows → list[list] 변환"""
    rows = []
    for row in response_rows:
        row_data = []
        for i, dim_value in enumerate(row.dimension_values):
            val = dim_value.value
            # 날짜 포맷 변환 (YYYYMMDD → YYYY-MM-DD)
            if len(val) == 8 and val.isdigit():
                val = f"{val[:4]}-{val[4:6]}-{val[6:]}"
            # pageReferrer 도메인 처리
            if headers[i] == "pageReferrer" and val:
                try:
                    parsed = urlparse(val)
                    if parsed.hostname and INTERNAL_DOMAIN in parsed.hostname:
                        val = parsed.path or "/"
                    elif parsed.hostname:
                        val = "(external)"
                except Exception:
                    pass
            row_data.append(val)
        for metric_value in row.metric_values:
            val = float(metric_value.value)
            if headers[len(row_data)] == "engagementRate":
                val = round(val * 100, 2)
            row_data.append(val)
        rows.append(row_data)
    return rows


def fetch_ga4_event_data(property_id: str, start_date: str, end_date: str) -> list[list]:
    """
    이벤트/페이지 기반 GA4 데이터 조회 → 포인트클릭_GA 시트용

    Dimensions: date, eventName, pageTitle, pagePath, customEvent:*
    Metrics: 이벤트·세션·참여 지표 (사용자 지표 제외)
    """
    client = get_ga4_client()

    request = RunReportRequest(
        property=property_id,
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimension_filter=_stream_filter(),
        dimensions=[
            Dimension(name="date"),
            Dimension(name="eventName"),
            Dimension(name="pageTitle"),
            Dimension(name="pagePath"),
            Dimension(name="customEvent:page_name"),
            Dimension(name="customEvent:page_type"),
            Dimension(name="customEvent:media_key"),
        ],
        metrics=[
            Metric(name="eventCount"),
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="averageSessionDuration"),
            Metric(name="engagementRate"),
            Metric(name="userEngagementDuration"),
        ],
        limit=100000,
    )

    headers = [dim.name for dim in request.dimensions] + [m.name for m in request.metrics]

    rows = []
    offset = 0
    while True:
        request.offset = offset
        request.limit = 100000
        response = client.run_report(request)
        rows.extend(_parse_rows(headers, response.rows))
        offset += len(response.rows)
        print(f"[sync] 포인트클릭_GA 조회 중: {offset} / {response.row_count}행")
        if offset >= response.row_count:
            break

    return [headers] + rows


def fetch_ga4_user_data(property_id: str, start_date: str, end_date: str) -> list[list]:
    """
    사용자 지표 GA4 데이터 조회 → 포인트클릭_GA_USER 시트용

    Dimensions: date 만 → 날짜당 1행 → DAU/WAU/MAU 정확
    Metrics: activeUsers, active7DayUsers, active28DayUsers, newUsers, sessions
    """
    client = get_ga4_client()

    request = RunReportRequest(
        property=property_id,
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimension_filter=_stream_filter(),
        dimensions=[
            Dimension(name="date"),
        ],
        metrics=[
            Metric(name="activeUsers"),       # DAU
            Metric(name="active7DayUsers"),   # WAU
            Metric(name="active28DayUsers"),  # MAU
            Metric(name="newUsers"),
            Metric(name="sessions"),
        ],
        limit=100000,
    )

    headers = [dim.name for dim in request.dimensions] + [m.name for m in request.metrics]

    rows = []
    offset = 0
    while True:
        request.offset = offset
        request.limit = 100000
        response = client.run_report(request)
        rows.extend(_parse_rows(headers, response.rows))
        offset += len(response.rows)
        print(f"[sync] 포인트클릭_GA_USER 조회 중: {offset} / {response.row_count}행")
        if offset >= response.row_count:
            break

    return [headers] + rows


def update_sheet(data: list[list], days: int, sheet_name: str):
    """Google Sheets에 누적 적재 (upsert: 수집 기간 내 날짜만 교체, 그 이전 데이터는 보존)"""
    gc = get_gspread_client()
    sh = gc.open_by_key(SPREADSHEET_ID)

    # 시트가 없으면 생성
    try:
        ws = sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=1000, cols=30)
        print(f"[sync] '{sheet_name}' 시트 신규 생성")

    new_headers = data[0]
    new_rows = data[1:]

    existing = ws.get_all_values()

    # 시트가 비어있으면 헤더 포함 전체 쓰기
    if not existing:
        ws.resize(rows=len(data) + 1, cols=len(data[0]))
        ws.update(range_name="A1", values=data)
        print(f"[sync] '{sheet_name}' 첫 적재: {len(new_rows)}행")
        return len(new_rows)

    existing_headers = existing[0]
    existing_rows = existing[1:]

    # 헤더가 바뀐 경우 전체 재작성
    if existing_headers != new_headers:
        print(f"[sync] '{sheet_name}' 헤더 변경 감지 → 전체 재작성")
        ws.clear()
        ws.resize(rows=len(data) + 1, cols=len(data[0]))
        ws.update(range_name="A1", values=data)
        return len(new_rows)

    date_idx = 0
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    new_dates = {row[date_idx] for row in new_rows if row}

    old_rows = [row for row in existing_rows if row and row[date_idx] < cutoff]
    replaced_rows = [row for row in existing_rows if row and row[date_idx] >= cutoff and row[date_idx] not in new_dates]

    merged = old_rows + replaced_rows + new_rows
    merged.sort(key=lambda r: r[date_idx] if r else "")

    final_data = [new_headers] + merged

    ws.clear()
    ws.resize(rows=len(final_data) + 1, cols=len(new_headers))
    ws.update(range_name="A1", values=final_data)

    added = len(new_dates - {row[date_idx] for row in existing_rows if row})
    updated = len(new_dates) - added
    print(f"[sync] '{sheet_name}' cutoff: {cutoff} | 이전 보존 {len(old_rows)}행 | 신규 {added}일 | 갱신 {updated}일")

    return len(merged)


def main():
    property_id = os.environ.get("GA4_POINTCLICK_PROPERTY_ID")

    if not property_id:
        print("[ERROR] GA4_POINTCLICK_PROPERTY_ID 환경변수가 설정되지 않았습니다.")
        print("[ERROR] GitHub Secret 'GA4_POINTCLICK_PROPERTY_ID' 값을 확인하세요.")
        sys.exit(1)

    if not SPREADSHEET_ID:
        print("[ERROR] SPREADSHEET_ID 환경변수가 비어있습니다.")
        print("[ERROR] GitHub Secret 'SPREADSHEET_ID_PC_GA' 값을 확인하세요.")
        sys.exit(1)

    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    else:
        days = DEFAULT_DAYS

    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"[sync] 포인트클릭 GA4 데이터 수집")
    print(f"[sync] 기간: {start_str} ~ {end_str} ({days}일)")
    print(f"[sync] Property ID: {property_id}")

    # ── 이벤트 데이터 → 포인트클릭_GA ──────────────────────────────
    event_data = fetch_ga4_event_data(property_id, start_str, end_str)

    if len(event_data) > 1:
        print(f"[sync] 이벤트 데이터 {len(event_data) - 1}행 조회 완료")

        # 매체 마스터 조인
        media_master = load_media_master()
        if media_master:
            headers = event_data[0]
            media_key_idx = next((i for i, h in enumerate(headers) if h == 'customEvent:media_key'), None)
            if media_key_idx is not None:
                insert_idx = media_key_idx + 1
                headers.insert(insert_idx, 'media_name')
                for i in range(1, len(event_data)):
                    row = event_data[i]
                    media_key = row[media_key_idx] if media_key_idx < len(row) else ""
                    row.insert(insert_idx, media_master.get(media_key, media_key))
                print("[sync] 매체명 조인 완료")

        count = update_sheet(event_data, days, SHEET_NAME_EVENT)
        print(f"[sync] {SHEET_NAME_EVENT}에 {count}행 적재 완료")
    else:
        print("[sync] 이벤트 데이터 없음")

    # ── 사용자 데이터 → 포인트클릭_GA_USER ─────────────────────────
    user_data = fetch_ga4_user_data(property_id, start_str, end_str)

    if len(user_data) > 1:
        print(f"[sync] 사용자 데이터 {len(user_data) - 1}행 조회 완료")
        count = update_sheet(user_data, days, SHEET_NAME_USER)
        print(f"[sync] {SHEET_NAME_USER}에 {count}행 적재 완료")
    else:
        print("[sync] 사용자 데이터 없음")


if __name__ == "__main__":
    main()
