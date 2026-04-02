"""
캐시플레이_DB 자동 적재 스크립트 (Supabase 버전)
- 원본 관리 시트(DATA_통합)에서 전일자 데이터를 읽어 Supabase cashplay_db 테이블에 upsert
- GitHub Actions에서 매일 오전 9시(KST) 실행
"""

import os
import json
import re
import sys
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

import gspread
from google.oauth2.service_account import Credentials
from supabase import create_client

# ============================================================
# 설정
# ============================================================
SOURCE_SPREADSHEET_ID = os.environ.get("SOURCE_SPREADSHEET_ID", "").strip()
SOURCE_SHEET_NAME = "DATA_통합"
TABLE_NAME = "cashplay_db"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# 원본 시트 컬럼 위치 (1-based)
DATE_COL = 2        # B열: 날짜
DATA_START_COL = 34  # AH열: 데이터 시작
DATA_END_COL = 58    # BF열: 데이터 끝

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# reward_total(AJ) 다음 5열(AK~AO)은 DB에 저장하지 않는 집계열이므로 건너뜀
# 시트 구조: AH(reward_paid) AI(reward_free) AJ(reward_total)
#            AK~AO(스킵 5열) AP(game_direct) ... BF(offerwall_total)
SKIP_AFTER_IDX = 3   # index 3부터 5열 스킵
SKIP_COUNT = 5

# Supabase 컬럼 순서 (총 20열, 스킵 열 제외)
CASHPLAY_COLUMNS = [
    "reward_paid", "reward_free", "reward_total",
    "game_direct", "game_dsp", "game_rs", "game_acquisition", "game_total",
    "gathering_pointclick",
    "iaa_levelplay", "iaa_adwhale", "iaa_hubble", "iaa_total",
    "offerwall_adpopcorn", "offerwall_pointclick", "offerwall_ive",
    "offerwall_adforus", "offerwall_addison", "offerwall_adjo", "offerwall_total"
]


def get_gspread_client():
    creds_json = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    return gspread.authorize(creds)


def get_supabase_client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


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

    # AH~BF열 데이터 가져오기 (AH=34, BF=58, 총 25열)
    range_str = f"AH{matched_row}:BF{matched_row}"
    row_data = ws.get(range_str)

    if not row_data or not row_data[0]:
        return None

    values = row_data[0]

    # reward_total 이후 5열(AK~AO)은 DB 저장 대상이 아니므로 제거
    values = values[:SKIP_AFTER_IDX] + values[SKIP_AFTER_IDX + SKIP_COUNT:]

    # 숫자 변환: 빈 문자열이나 '-'는 0으로
    formatted = []
    for val in values:
        val_str = str(val).strip()
        if val_str == "" or val_str == "-":
            formatted.append(0)
        else:
            try:
                num = float(val_str.replace(",", ""))
                formatted.append(int(num) if num == int(num) else num)
            except ValueError:
                formatted.append(0)

    return formatted


def check_date_exists(client, target_date: str) -> bool:
    """Supabase 테이블에 해당 날짜 데이터가 이미 있는지 확인."""
    response = client.table(TABLE_NAME).select("date").eq("date", target_date).limit(1).execute()
    return len(response.data) > 0


def parse_date_range(args: list[str]) -> tuple[list[str], bool]:
    """인자를 파싱하여 (날짜 리스트, force 여부)를 반환한다.

    지원 형식:
      sync_cashplay.py                          → 전일자 1건
      sync_cashplay.py 2026-03-15               → 단일 날짜
      sync_cashplay.py 2026-03-13 2026-03-17    → 시작~끝 범위
      sync_cashplay.py --force ...              → 기존 데이터 덮어쓰기
    """
    force = "--force" in args
    dates = [a for a in args if a != "--force"]

    if len(dates) == 0:
        today = datetime.now(KST)
        return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7, 0, -1)], True
    elif len(dates) == 1:
        return [dates[0]], force
    else:
        start = datetime.strptime(dates[0], "%Y-%m-%d")
        end = datetime.strptime(dates[1], "%Y-%m-%d")
        day_count = (end - start).days + 1
        return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(day_count)], force


def sync_one_date(gc, client, target_date: str, force: bool) -> bool:
    """단일 날짜를 동기화한다. 성공 시 True 반환."""
    if not force and check_date_exists(client, target_date):
        print(f"[sync] {target_date} 데이터가 이미 존재합니다. 건너뜁니다. (--force 로 덮어쓰기 가능)")
        return False

    data = fetch_from_source(gc, target_date)
    if data is None:
        print(f"[sync] {target_date} 데이터가 원본 시트에 없습니다.")
        return False

    row = {"date": target_date}
    for i, col_name in enumerate(CASHPLAY_COLUMNS):
        row[col_name] = data[i] if i < len(data) else 0

    client.table(TABLE_NAME).upsert(row, on_conflict="date").execute()
    print(f"[sync] {target_date} → Supabase 적재 완료")
    return True


def main():
    if not SOURCE_SPREADSHEET_ID:
        print("[ERROR] SOURCE_SPREADSHEET_ID 환경변수가 비어있습니다.")
        sys.exit(1)

    print(f"[sync] 캐시플레이 DB 동기화 시작")
    print(f"[sync] SOURCE_ID: {SOURCE_SPREADSHEET_ID[:4]}...{SOURCE_SPREADSHEET_ID[-4:]}")

    target_dates, force = parse_date_range(sys.argv[1:])
    print(f"[sync] 대상 날짜: {', '.join(target_dates)} (force={force})")

    client = get_supabase_client()
    gc = get_gspread_client()

    success_count = 0
    for d in target_dates:
        if sync_one_date(gc, client, d, force):
            success_count += 1

    print(f"[sync] 완료: {success_count}/{len(target_dates)}건 적재")


if __name__ == "__main__":
    main()
