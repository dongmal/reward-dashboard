"""
캐시플레이_DB 시트 자동 적재 스크립트
- 원본 관리 시트(DATA_통합)에서 전일자 데이터를 읽어 대시보드 시트에 append
- GitHub Actions에서 매일 오전 9시(KST) 실행
"""

import os
import json
import re
import sys
from datetime import datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

# ============================================================
# 설정
# ============================================================
SOURCE_SPREADSHEET_ID = os.environ.get("SOURCE_SPREADSHEET_ID")
TARGET_SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SOURCE_SHEET_NAME = "DATA_통합"
TARGET_SHEET_NAME = "캐시플레이_DB"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# 원본 시트 컬럼 위치 (1-based)
DATE_COL = 2        # B열: 날짜
DATA_START_COL = 32  # AF열: 데이터 시작
DATA_END_COL = 51    # AY열: 데이터 끝

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def get_gspread_client():
    creds_json = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    return gspread.authorize(creds)


def fetch_from_source(gc, target_date: str) -> list | None:
    """원본 시트에서 target_date에 해당하는 행의 AF~AY 데이터를 가져온다."""
    sh = gc.open_by_key(SOURCE_SPREADSHEET_ID)
    ws = sh.worksheet(SOURCE_SHEET_NAME)

    # B열 전체 가져오기
    b_col = ws.col_values(DATE_COL)

    # YYYY-MM-DD 형식인 셀 중에서 target_date와 일치하는 행 찾기
    matched_row = None
    for i, cell in enumerate(b_col):
        cell_stripped = str(cell).strip()
        if DATE_PATTERN.match(cell_stripped) and cell_stripped == target_date:
            matched_row = i + 1  # gspread는 1-based
            break

    if matched_row is None:
        return None

    # AF~AY열 데이터 가져오기 (AF=32, AY=51)
    range_str = f"AF{matched_row}:AY{matched_row}"
    row_data = ws.get(range_str)

    if not row_data or not row_data[0]:
        return None

    values = row_data[0]

    # 숫자 변환: 빈 문자열이나 '-'는 0으로
    formatted = []
    for val in values:
        val_str = str(val).strip()
        if val_str == "" or val_str == "-":
            formatted.append(0)
        else:
            try:
                # 콤마 제거 후 숫자 변환
                num = float(val_str.replace(",", ""))
                formatted.append(int(num) if num == int(num) else num)
            except ValueError:
                formatted.append(val_str)

    return formatted


def check_date_exists(ws, target_date: str) -> bool:
    """대상 시트에 해당 날짜 데이터가 이미 있는지 확인."""
    date_col = ws.col_values(1)  # 날짜 컬럼 (A열)
    return target_date in date_col


def main():
    # 대상 날짜: 전일자 (또는 인자로 지정)
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        yesterday = datetime.now() - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")

    print(f"[sync] 대상 날짜: {target_date}")

    gc = get_gspread_client()

    # 1. 대상 시트에서 중복 체크
    target_sh = gc.open_by_key(TARGET_SPREADSHEET_ID)
    target_ws = target_sh.worksheet(TARGET_SHEET_NAME)

    if check_date_exists(target_ws, target_date):
        print(f"[sync] {target_date} 데이터가 이미 존재합니다. 건너뜁니다.")
        return

    # 2. 원본 시트에서 데이터 가져오기
    data = fetch_from_source(gc, target_date)

    if data is None:
        print(f"[sync] {target_date} 데이터가 원본 시트에 없습니다.")
        return

    print(f"[sync] 원본 시트에서 {len(data)}개 컬럼 조회 완료")

    # 3. [날짜, 데이터...] 형태로 append
    row = [target_date] + data
    target_ws.append_rows([row], value_input_option="USER_ENTERED")
    print(f"[sync] 캐시플레이_DB에 1행 적재 완료")


if __name__ == "__main__":
    main()
