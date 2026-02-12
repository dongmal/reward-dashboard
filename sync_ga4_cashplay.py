"""
캐시플레이_GA 시트 자동 적재 스크립트
- GA4에서 전일자 데이터를 조회하여 Google Sheets에 덮어쓰기
- GitHub Actions에서 매일 오전 9시(KST) 실행
"""

import os
import json
import sys
from datetime import datetime, timedelta

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
SHEET_NAME = "캐시플레이_GA"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/analytics.readonly"
]

# GA4 수집 기간 (최근 N일)
DEFAULT_DAYS = 90


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


def fetch_ga4_data(property_id: str, start_date: str, end_date: str) -> list[list]:
    """
    GA4에서 이벤트 기반 데이터 조회
    - 메뉴별 세션 타임, 클릭수, 참여율 분석 가능
    - DAU/WAU/MAU 사용자 지표 포함

    Args:
        property_id: GA4 속성 ID (예: "properties/123456789")
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)

    Returns:
        헤더 + 데이터 행 리스트
    """
    client = get_ga4_client()

    request = RunReportRequest(
        property=property_id,
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="streamName",
                string_filter=Filter.StringFilter(
                    match_type=Filter.StringFilter.MatchType.EXACT,
                    value="캐시플레이",
                ),
            )
        ),
        dimensions=[
            # 기본 차원
            Dimension(name="date"),
            Dimension(name="eventName"),

            # 페이지/메뉴 추적
            Dimension(name="pageTitle"),
            Dimension(name="pagePath"),
            Dimension(name="landingPagePlusQueryString"),  # 유입 경로

            # 커스텀 이벤트 차원 (메뉴/버튼 클릭 추적)
            Dimension(name="customEvent:page"),
            Dimension(name="customEvent:page_type"),
            Dimension(name="customEvent:button_id"),

        ],
        metrics=[
            # 사용자 지표 (DAU/WAU/MAU)
            Metric(name="activeUsers"),  # DAU
            Metric(name="active7DayUsers"),  # WAU
            Metric(name="active28DayUsers"),  # MAU
            Metric(name="newUsers"),

            # 이벤트/세션 지표
            Metric(name="eventCount"),
            Metric(name="sessions"),
            Metric(name="screenPageViews"),

            # 참여 지표
            Metric(name="averageSessionDuration"),
            Metric(name="engagementRate"),
            Metric(name="userEngagementDuration"),
        ],
        limit=100000,
    )

    response = client.run_report(request)

    # 헤더
    headers = [dim.name for dim in request.dimensions] + [metric.name for metric in request.metrics]

    # 데이터 행
    rows = []
    for row in response.rows:
        row_data = []

        # Dimensions
        for dim_value in row.dimension_values:
            val = dim_value.value
            # 날짜 포맷 변환 (20240101 -> 2024-01-01)
            if len(val) == 8 and val.isdigit():
                val = f"{val[:4]}-{val[4:6]}-{val[6:]}"
            row_data.append(val)

        # Metrics
        for metric_value in row.metric_values:
            val = float(metric_value.value)
            # engagementRate는 비율이므로 100 곱하기
            if headers[len(row_data)] == "engagementRate":
                val = round(val * 100, 2)
            row_data.append(val)

        rows.append(row_data)

    return [headers] + rows


def update_sheet(data: list[list]):
    """Google Sheets에 데이터 덮어쓰기 (전체 삭제 후 새로 씀)"""
    gc = get_gspread_client()
    sh = gc.open_by_key(SPREADSHEET_ID)

    # 시트가 없으면 생성
    try:
        ws = sh.worksheet(SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_NAME, rows=1000, cols=20)

    # 기존 데이터 삭제
    ws.clear()

    # 새 데이터 쓰기
    ws.update(range_name="A1", values=data)

    return len(data) - 1  # 헤더 제외 행 수


def main():
    property_id = os.environ.get("GA4_CASHPLAY_PROPERTY_ID")

    if not property_id:
        print("[ERROR] GA4_CASHPLAY_PROPERTY_ID 환경변수가 설정되지 않았습니다.")
        print("GitHub Secrets에 GA4_CASHPLAY_PROPERTY_ID를 추가하세요.")
        sys.exit(1)

    # 날짜 범위 계산
    if len(sys.argv) > 1:
        # 인자로 일수 지정 가능
        days = int(sys.argv[1])
    else:
        days = DEFAULT_DAYS

    end_date = datetime.now() - timedelta(days=1)  # 어제
    start_date = end_date - timedelta(days=days - 1)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"[sync] 캐시플레이 GA4 데이터 수집")
    print(f"[sync] 기간: {start_str} ~ {end_str} ({days}일)")
    print(f"[sync] Property ID: {property_id}")

    # GA4 데이터 조회
    data = fetch_ga4_data(property_id, start_str, end_str)

    if len(data) <= 1:  # 헤더만 있음
        print("[sync] GA4에 데이터가 없습니다.")
        return

    print(f"[sync] GA4에서 {len(data) - 1}행 조회 완료")

    # Google Sheets에 덮어쓰기
    count = update_sheet(data)
    print(f"[sync] Google Sheets에 {count}행 적재 완료")


if __name__ == "__main__":
    main()
