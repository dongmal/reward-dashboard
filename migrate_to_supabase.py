"""
Google Sheets → Supabase 데이터 마이그레이션 스크립트
- 기존 Google Sheets 데이터를 Supabase로 일괄 이전
- 로컬 또는 GitHub Actions에서 1회 실행

사용법:
    python migrate_to_supabase.py [--tables all|pointclick_db|cashplay_db|pointclick_ga|cashplay_ga|media_master]

필요 환경변수:
    SUPABASE_URL, SUPABASE_KEY
    GCP_SERVICE_ACCOUNT
    SPREADSHEET_ID    - 모든 시트가 들어있는 스프레드시트 ID (한 파일에 시트로 구분된 경우)

    ※ 스프레드시트가 파일별로 분리된 경우 개별 지정도 가능 (SPREADSHEET_ID가 없을 때 fallback):
    SPREADSHEET_ID_PC_DB, SPREADSHEET_ID_PC_GA
    SPREADSHEET_ID_CP_DB, SPREADSHEET_ID_CP_GA
"""

import os
import sys
import json
import argparse
from datetime import datetime

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from supabase import create_client

# ============================================================
# 설정
# ============================================================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# 시트명 매핑: Supabase 테이블 → (구 env 변수명(fallback), 시트명)
# SPREADSHEET_ID 단일 환경변수가 있으면 그것을 우선 사용
SHEET_TO_TABLE = {
    "pointclick_db":      ("SPREADSHEET_ID_PC_DB", "포인트클릭_DB"),
    "cashplay_db":        ("SPREADSHEET_ID_CP_DB", "캐시플레이_DB"),
    "pointclick_ga":      ("SPREADSHEET_ID_PC_GA", "포인트클릭_GA"),
    "pointclick_ga_user": ("SPREADSHEET_ID_PC_GA", "포인트클릭_GA_USER"),
    "cashplay_ga":        ("SPREADSHEET_ID_CP_GA", "캐시플레이_GA"),
    "cashplay_ga_user":   ("SPREADSHEET_ID_CP_GA", "캐시플레이_GA_USER"),
    "media_master":       ("SPREADSHEET_ID_PC_GA", "매체마스터"),
}

# 포인트클릭 DB 컬럼 매핑 (한글 → 영어)
PC_DB_COL_MAP = {
    '일자': 'date', '광고구분': 'ad_category', '매체타입': 'media_type',
    '퍼블리셔타입': 'publisher_type', '광고명': 'ad_name', '매체명': 'media_name',
    'CD': 'cd', '광고주명': 'advertiser', 'OS': 'os', '광고타입': 'ad_type',
    '광고단가': 'unit_price', '클릭수': 'clicks', '전환수': 'conversions',
    '광고비': 'ad_revenue', '매체수익금': 'media_cost', '매체정산비율': 'media_rate',
    '마진금액': 'margin', '마진율': 'margin_rate', 'CVR': 'cvr',
    '주차': 'week', '월별': 'month'
}

# 캐시플레이 DB 컬럼 매핑
CP_DB_COL_MAP = {
    '날짜': 'date',
    '리워드(원)_유상': 'reward_paid', '리워드(원)_무상': 'reward_free', '리워드(원)_합계': 'reward_total',
    '게임(원)_직거래': 'game_direct', '게임(원)_DSP': 'game_dsp', '게임(원)_RS': 'game_rs',
    '게임(원)_인수': 'game_acquisition', '게임(원)_합계': 'game_total',
    '게더링(원)_포인트클릭': 'gathering_pointclick',
    'IAA(원)_레벨플레이': 'iaa_levelplay', 'IAA(원)_애드웨일': 'iaa_adwhale',
    'IAA(원)_허블': 'iaa_hubble', 'IAA(원)_합계': 'iaa_total',
    '오퍼월(원)_애드팝콘': 'offerwall_adpopcorn', '오퍼월(원)_포인트클릭': 'offerwall_pointclick',
    '오퍼월(원)_아이브': 'offerwall_ive', '오퍼월(원)_애드포러스': 'offerwall_adforus',
    '오퍼월(원)_애디슨': 'offerwall_addison', '오퍼월(원)_애드조': 'offerwall_adjo',
    '오퍼월(원)_합계': 'offerwall_total'
}

# GA4 이벤트 컬럼 매핑 (customEvent:xxx → xxx)
GA_EVENT_COL_MAP = {
    'customEvent:page_name': 'page_name',
    'customEvent:page_type': 'page_type',
    'customEvent:media_key': 'media_key',
    'customEvent:page': 'page',
    'customEvent:button_id': 'button_id',
}

# 매체마스터 컬럼 매핑
MEDIA_COL_MAP = {
    '매체키': 'media_key',
    '매체명': 'media_name',
}


# ============================================================
# 클라이언트
# ============================================================
def get_gspread_client():
    creds_json = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    return gspread.authorize(creds)


def get_supabase_client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


# ============================================================
# Google Sheets 읽기
# ============================================================
def read_sheet(sheet_name: str, fallback_id_env: str = None) -> pd.DataFrame:
    """Google Sheets에서 전체 데이터 읽기.

    SPREADSHEET_ID 환경변수를 우선 사용하고,
    없으면 fallback_id_env 이름의 개별 환경변수를 시도합니다.
    """
    # 단일 파일 우선
    spreadsheet_id = os.environ.get("SPREADSHEET_ID", "").strip()

    # fallback: 개별 env 변수
    if not spreadsheet_id and fallback_id_env:
        spreadsheet_id = os.environ.get(fallback_id_env, "").strip()
        if spreadsheet_id:
            print(f"[info] SPREADSHEET_ID 없음 → {fallback_id_env} 사용")

    if not spreadsheet_id:
        missing = "SPREADSHEET_ID" + (f" / {fallback_id_env}" if fallback_id_env else "")
        print(f"[WARN] {missing} 환경변수가 없습니다. '{sheet_name}' 건너뜁니다.")
        return pd.DataFrame()

    gc = get_gspread_client()
    try:
        sh = gc.open_by_key(spreadsheet_id)
        ws = sh.worksheet(sheet_name)
        data = ws.get_all_values()
        if not data or len(data) < 2:
            print(f"[WARN] '{sheet_name}' 시트에 데이터가 없습니다.")
            return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=data[0])
        print(f"[read] '{sheet_name}' → {len(df)}행 읽기 완료")
        return df
    except Exception as e:
        print(f"[ERROR] '{sheet_name}' 읽기 실패: {e}")
        return pd.DataFrame()


# ============================================================
# 전처리 함수
# ============================================================
def _to_numeric(val):
    if val is None or val == "" or val == "-":
        return 0
    try:
        v = str(val).replace(",", "")
        f = float(v)
        return int(f) if f == int(f) else round(f, 6)
    except (ValueError, TypeError):
        return 0


def process_pointclick_db(df: pd.DataFrame) -> list:
    df = df.rename(columns=PC_DB_COL_MAP)
    if 'date' not in df.columns:
        return []

    numeric_cols = ['unit_price', 'clicks', 'conversions', 'ad_revenue', 'media_cost',
                    'media_rate', 'margin', 'margin_rate', 'cvr']
    rows = []
    for _, row in df.iterrows():
        date_val = str(row.get('date', '')).strip()
        if not date_val or date_val == 'nan':
            continue
        rec = {'date': date_val}
        for col in PC_DB_COL_MAP.values():
            if col == 'date':
                continue
            val = row.get(col, '')
            if col in numeric_cols:
                rec[col] = _to_numeric(val)
            else:
                rec[col] = str(val) if val and str(val) != 'nan' else None
        rows.append(rec)
    return rows


def process_cashplay_db(df: pd.DataFrame) -> list:
    df = df.rename(columns=CP_DB_COL_MAP)
    if 'date' not in df.columns:
        return []

    numeric_cols = [c for c in CP_DB_COL_MAP.values() if c != 'date']
    rows = []
    for _, row in df.iterrows():
        date_val = str(row.get('date', '')).strip()
        if not date_val or date_val == 'nan':
            continue
        rec = {'date': date_val}
        for col in numeric_cols:
            rec[col] = _to_numeric(row.get(col, 0))
        rows.append(rec)
    return rows


def process_ga_event(df: pd.DataFrame, table_name: str) -> list:
    """GA4 이벤트 데이터 전처리 (customEvent:* 컬럼명 변환)"""
    df = df.rename(columns=GA_EVENT_COL_MAP)
    if 'date' not in df.columns:
        return []

    numeric_cols = {'eventCount', 'sessions', 'screenPageViews',
                    'averageSessionDuration', 'engagementRate', 'userEngagementDuration'}
    rows = []
    for _, row in df.iterrows():
        date_val = str(row.get('date', '')).strip()
        if not date_val or date_val == 'nan':
            continue
        rec = {}
        for col in df.columns:
            val = row.get(col)
            if col == 'date':
                rec[col] = date_val
            elif col in numeric_cols:
                rec[col] = _to_numeric(val)
            else:
                rec[col] = str(val) if val and str(val) != 'nan' else None
        rows.append(rec)
    return rows


def process_ga_user(df: pd.DataFrame) -> list:
    """GA4 사용자 데이터 전처리"""
    if 'date' not in df.columns:
        return []

    numeric_cols = {'activeUsers', 'active7DayUsers', 'active28DayUsers', 'newUsers', 'sessions'}
    rows = []
    for _, row in df.iterrows():
        date_val = str(row.get('date', '')).strip()
        if not date_val or date_val == 'nan':
            continue
        rec = {'date': date_val}
        for col in numeric_cols:
            rec[col] = _to_numeric(row.get(col, 0))
        rows.append(rec)
    return rows


def process_media_master(df: pd.DataFrame) -> list:
    df = df.rename(columns=MEDIA_COL_MAP)
    if 'media_key' not in df.columns:
        return []
    rows = []
    for _, row in df.iterrows():
        key = str(row.get('media_key', '')).strip()
        name = str(row.get('media_name', '')).strip()
        if key and key != 'nan':
            rows.append({'media_key': key, 'media_name': name if name != 'nan' else ''})
    return rows


# ============================================================
# Supabase 삽입
# ============================================================
def insert_to_supabase(client, table_name: str, rows: list, on_conflict: str = None):
    """Supabase에 데이터 삽입 (1000행 단위 청크)"""
    if not rows:
        print(f"[insert] {table_name}: 삽입할 데이터 없음")
        return 0

    chunk_size = 1000
    total = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        if on_conflict:
            client.table(table_name).upsert(chunk, on_conflict=on_conflict).execute()
        else:
            client.table(table_name).insert(chunk).execute()
        total += len(chunk)
        print(f"[insert] {table_name}: {total}/{len(rows)}행 완료")

    print(f"[insert] {table_name}: 총 {total}행 적재 완료")
    return total


# ============================================================
# 마이그레이션 함수별
# ============================================================
def migrate_pointclick_db(client):
    print("\n=== 포인트클릭 DB 마이그레이션 ===")
    df = read_sheet("포인트클릭_DB", fallback_id_env="SPREADSHEET_ID_PC_DB")
    if df.empty:
        return
    rows = process_pointclick_db(df)
    print(f"[process] {len(rows)}행 전처리 완료")
    # 기존 데이터 삭제 후 전체 재삽입
    print("[delete] pointclick_db 기존 데이터 전체 삭제 중...")
    client.table("pointclick_db").delete().neq("id", 0).execute()
    insert_to_supabase(client, "pointclick_db", rows)


def migrate_cashplay_db(client):
    print("\n=== 캐시플레이 DB 마이그레이션 ===")
    df = read_sheet("캐시플레이_DB", fallback_id_env="SPREADSHEET_ID_CP_DB")
    if df.empty:
        return
    rows = process_cashplay_db(df)
    print(f"[process] {len(rows)}행 전처리 완료")
    insert_to_supabase(client, "cashplay_db", rows, on_conflict="date")


def migrate_pointclick_ga(client):
    print("\n=== 포인트클릭 GA 마이그레이션 ===")
    df = read_sheet("포인트클릭_GA", fallback_id_env="SPREADSHEET_ID_PC_GA")
    if df.empty:
        return
    rows = process_ga_event(df, "pointclick_ga")
    print(f"[process] {len(rows)}행 전처리 완료")
    print("[delete] pointclick_ga 기존 데이터 전체 삭제 중...")
    client.table("pointclick_ga").delete().neq("id", 0).execute()
    insert_to_supabase(client, "pointclick_ga", rows)


def migrate_pointclick_ga_user(client):
    print("\n=== 포인트클릭 GA_USER 마이그레이션 ===")
    df = read_sheet("포인트클릭_GA_USER", fallback_id_env="SPREADSHEET_ID_PC_GA")
    if df.empty:
        return
    rows = process_ga_user(df)
    print(f"[process] {len(rows)}행 전처리 완료")
    insert_to_supabase(client, "pointclick_ga_user", rows, on_conflict="date")


def migrate_cashplay_ga(client):
    print("\n=== 캐시플레이 GA 마이그레이션 ===")
    df = read_sheet("캐시플레이_GA", fallback_id_env="SPREADSHEET_ID_CP_GA")
    if df.empty:
        return
    rows = process_ga_event(df, "cashplay_ga")
    print(f"[process] {len(rows)}행 전처리 완료")
    print("[delete] cashplay_ga 기존 데이터 전체 삭제 중...")
    client.table("cashplay_ga").delete().neq("id", 0).execute()
    insert_to_supabase(client, "cashplay_ga", rows)


def migrate_cashplay_ga_user(client):
    print("\n=== 캐시플레이 GA_USER 마이그레이션 ===")
    df = read_sheet("캐시플레이_GA_USER", fallback_id_env="SPREADSHEET_ID_CP_GA")
    if df.empty:
        return
    rows = process_ga_user(df)
    print(f"[process] {len(rows)}행 전처리 완료")
    insert_to_supabase(client, "cashplay_ga_user", rows, on_conflict="date")


def migrate_media_master(client):
    print("\n=== 매체마스터 마이그레이션 ===")
    df = read_sheet("매체마스터", fallback_id_env="SPREADSHEET_ID_PC_GA")
    if df.empty:
        return
    rows = process_media_master(df)
    print(f"[process] {len(rows)}개 매체 전처리 완료")
    insert_to_supabase(client, "media_master", rows, on_conflict="media_key")


# ============================================================
# 메인
# ============================================================
MIGRATE_FUNCS = {
    "pointclick_db":      migrate_pointclick_db,
    "cashplay_db":        migrate_cashplay_db,
    "pointclick_ga":      migrate_pointclick_ga,
    "pointclick_ga_user": migrate_pointclick_ga_user,
    "cashplay_ga":        migrate_cashplay_ga,
    "cashplay_ga_user":   migrate_cashplay_ga_user,
    "media_master":       migrate_media_master,
}


def main():
    parser = argparse.ArgumentParser(description="Google Sheets → Supabase 마이그레이션")
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["all"],
        choices=list(MIGRATE_FUNCS.keys()) + ["all"],
        help="마이그레이션할 테이블 (기본: all)"
    )
    args = parser.parse_args()

    tables = list(MIGRATE_FUNCS.keys()) if "all" in args.tables else args.tables

    print(f"[migrate] 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[migrate] 대상 테이블: {', '.join(tables)}")

    client = get_supabase_client()

    for table in tables:
        try:
            MIGRATE_FUNCS[table](client)
        except Exception as e:
            print(f"[ERROR] {table} 마이그레이션 실패: {e}")

    print(f"\n[migrate] 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
