"""
매체마스터 시트 자동 생성 스크립트
- MySQL media 테이블에서 media_key, media_name 직접 조회
- 매체마스터 시트에 저장
"""

import os
import json
import pymysql
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
MEDIA_MASTER_SHEET = "매체마스터"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SQL_QUERY = "SELECT media_key, media_name FROM media ORDER BY media_key"


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
    """Google Sheets 클라이언트 생성"""
    creds_json = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    return gspread.authorize(creds)


def fetch_media_from_mysql() -> list:
    """MySQL media 테이블에서 media_key, media_name 조회"""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(SQL_QUERY)
            rows = cursor.fetchall()
    finally:
        conn.close()

    print(f"[sync] MySQL에서 {len(rows)}개 매체 조회 완료")
    return rows


def create_media_master(rows: list):
    """매체마스터 시트 생성 및 데이터 저장"""
    gc = get_gspread_client()
    sh = gc.open_by_key(SPREADSHEET_ID)

    # 시트가 없으면 생성
    try:
        ws = sh.worksheet(MEDIA_MASTER_SHEET)
        print(f"[sync] 기존 '{MEDIA_MASTER_SHEET}' 시트 사용")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=MEDIA_MASTER_SHEET, rows=1000, cols=5)
        print(f"[sync] '{MEDIA_MASTER_SHEET}' 시트 생성")

    # 데이터 준비 (헤더 + 데이터)
    data = [["매체키", "매체명"]]
    for media_key, media_name in rows:
        data.append([str(media_key), str(media_name) if media_name else ""])

    # 기존 데이터 삭제 후 새 데이터 쓰기
    ws.clear()
    ws.update(range_name="A1", values=data)

    print(f"[sync] 매체마스터 시트에 {len(data) - 1}개 매체 저장 완료")

    # 샘플 출력
    print("\n[샘플 데이터]")
    for row in data[:6]:  # 헤더 + 5개만 출력
        print(f"  {str(row[0]):20} | {row[1]}")
    if len(data) > 6:
        print(f"  ... (총 {len(data) - 1}개)")


def main():
    if not SPREADSHEET_ID:
        print("[ERROR] SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")
        return

    print(f"[sync] 매체마스터 자동 생성 시작")

    # 1. MySQL에서 media_key, media_name 직접 조회
    rows = fetch_media_from_mysql()

    if not rows:
        print("[ERROR] MySQL media 테이블에 데이터가 없습니다.")
        return

    # 2. 매체마스터 시트 저장
    create_media_master(rows)

    print(f"\n[완료] 매체마스터 생성 완료!")


if __name__ == "__main__":
    main()
