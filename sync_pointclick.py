"""
포인트클릭_DB 시트 자동 적재 스크립트
- MySQL에서 전일자 데이터를 조회하여 Google Sheets에 append
- GitHub Actions에서 매일 오전 9시(KST) 실행
"""

import os
import json
import sys
from datetime import datetime, timedelta

import pymysql
import gspread
from google.oauth2.service_account import Credentials

# ============================================================
# 설정
# ============================================================
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SHEET_NAME = "포인트클릭_DB"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SQL_QUERY = """
SELECT
    rda.report_date as '일자',
    CASE WHEN rda.dsp_key = 0 THEN '직거래광고' ELSE '대행광고' END AS '광고구분',
    m.media_type as '매체타입',
    COALESCE(p.publisher_type, '미지정') as '퍼블리셔타입',
    a.ad_name as '광고명',
    m.media_name as '매체명',
    a.ad_key as 'CD',
    a2.advertiser_name as '광고주명',
    a.os_type as 'OS',
    a.ad_action_type as '광고타입',
    a.ad_cost as '광고단가',
    SUM(rda.check_count) as '클릭수',
    SUM(rda.complete_count) as '전환수',
    SUM(rda.cost_sum) as '광고비',
    SUM(rda.media_cost_sum) as '매체수익금',
    SUM(rda.media_cost_sum) / NULLIF(SUM(rda.cost_sum), 0) as '매체정산비율',
    SUM(rda.cost_sum) - SUM(rda.media_cost_sum) as '마진금액',
    (SUM(rda.cost_sum) - SUM(rda.media_cost_sum)) / NULLIF(SUM(rda.cost_sum), 0) as '마진율',
    SUM(rda.complete_count) / NULLIF(SUM(rda.check_count), 0) as CVR,
    CONCAT(FLOOR((DAY(rda.report_date) - 1) / 7) + 1, '주차') AS '주차',
    DATE_FORMAT(rda.report_date, '%%y년 %%c월') AS '월별'
FROM report_daily_ad rda
LEFT JOIN publisher p ON p.publisher_key = rda.publisher_key
LEFT JOIN ad a ON a.ad_key = rda.ad_key
LEFT JOIN media m ON m.media_key = rda.media_key
LEFT JOIN advertiser a2 ON a2.advertiser_key = rda.advertiser_key
WHERE rda.report_date = %s
  AND rda.check_count > 0
GROUP BY
    rda.report_date,
    rda.dsp_key,
    rda.advertiser_key,
    rda.publisher_key,
    rda.ad_key,
    rda.media_key
"""


def get_mysql_connection():
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ.get("MYSQL_PORT", 3306)),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
    )


def get_gspread_client():
    creds_json = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    return gspread.authorize(creds)


def fetch_data_from_mysql(target_date: str) -> list[list]:
    """MySQL에서 target_date 데이터를 조회하여 리스트로 반환."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(SQL_QUERY, (target_date,))
            rows = cursor.fetchall()
    finally:
        conn.close()

    result = []
    for row in rows:
        formatted = []
        for val in row:
            if val is None:
                formatted.append("")
            elif isinstance(val, (datetime,)):
                formatted.append(val.strftime("%Y-%m-%d"))
            elif isinstance(val, timedelta):
                formatted.append(str(val))
            elif isinstance(val, float):
                formatted.append(round(val, 6))
            else:
                formatted.append(str(val) if not isinstance(val, (int, float)) else val)
        result.append(formatted)

    return result


def check_date_exists(worksheet, target_date: str) -> bool:
    """시트에 해당 날짜 데이터가 이미 있는지 확인."""
    date_col = worksheet.col_values(1)  # 일자 컬럼 (A열)
    return target_date in date_col


def append_to_sheet(rows: list[list]):
    """Google Sheets에 데이터를 append."""
    gc = get_gspread_client()
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_NAME)
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    return len(rows)


def main():
    # 대상 날짜: 전일자 (또는 인자로 지정)
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        yesterday = datetime.now() - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")

    print(f"[sync] 대상 날짜: {target_date}")

    # 1. 중복 체크
    gc = get_gspread_client()
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_NAME)

    if check_date_exists(ws, target_date):
        print(f"[sync] {target_date} 데이터가 이미 존재합니다. 건너뜁니다.")
        return

    # 2. MySQL에서 데이터 조회
    rows = fetch_data_from_mysql(target_date)

    if not rows:
        print(f"[sync] {target_date} 데이터가 MySQL에 없습니다.")
        return

    print(f"[sync] MySQL에서 {len(rows)}행 조회 완료")

    # 3. Google Sheets에 append
    count = append_to_sheet(rows)
    print(f"[sync] Google Sheets에 {count}행 적재 완료")


if __name__ == "__main__":
    main()
