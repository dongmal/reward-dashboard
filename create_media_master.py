"""
매체마스터 시트 자동 생성 스크립트
- 포인트클릭_DB에서 unique media_name 추출
- media_key를 media_name의 소문자/공백제거 버전으로 생성
- 매체마스터 시트에 저장
"""

import os
import json
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
PC_DB_SHEET = "포인트클릭_DB"
MEDIA_MASTER_SHEET = "매체마스터"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_gspread_client():
    """Google Sheets 클라이언트 생성"""
    creds_json = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    return gspread.authorize(creds)


def generate_media_key(media_name: str) -> str:
    """매체명에서 매체키 생성 (소문자, 공백/특수문자 제거)"""
    if not media_name:
        return ""

    # 소문자 변환 및 공백/특수문자 제거
    key = media_name.lower()
    key = key.replace(" ", "_")
    key = key.replace("-", "_")
    key = key.replace("(", "")
    key = key.replace(")", "")
    key = key.replace(".", "")
    key = key.replace(",", "")

    return key


def extract_unique_media_names():
    """포인트클릭_DB에서 unique media_name 추출"""
    gc = get_gspread_client()
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(PC_DB_SHEET)
    data = ws.get_all_values()

    if not data or len(data) < 2:
        print("[ERROR] 포인트클릭_DB 시트가 비어있습니다.")
        return []

    # 헤더에서 매체명 컬럼 찾기
    headers = data[0]
    media_name_idx = None

    for i, h in enumerate(headers):
        if h == '매체명' or h == 'media_name':
            media_name_idx = i
            break

    if media_name_idx is None:
        print("[ERROR] 포인트클릭_DB에 '매체명' 컬럼이 없습니다.")
        return []

    # unique media_name 추출
    media_names = set()
    for row in data[1:]:
        if len(row) > media_name_idx:
            name = row[media_name_idx]
            if name and name.strip():
                media_names.add(name.strip())

    print(f"[sync] 포인트클릭_DB에서 {len(media_names)}개 매체명 추출")
    return sorted(list(media_names))


def create_media_master(media_names: list):
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

    # 데이터 준비
    data = [["매체키", "매체명"]]  # 헤더

    for media_name in media_names:
        media_key = generate_media_key(media_name)
        data.append([media_key, media_name])

    # 기존 데이터 삭제 후 새 데이터 쓰기
    ws.clear()
    ws.update(range_name="A1", values=data)

    print(f"[sync] 매체마스터 시트에 {len(data) - 1}개 매체 저장 완료")
    print(f"[sync] 시트 URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")

    # 샘플 출력
    print("\n[샘플 데이터]")
    for i, row in enumerate(data[:6]):  # 헤더 + 5개만 출력
        print(f"  {row[0]:20} | {row[1]}")
    if len(data) > 6:
        print(f"  ... (총 {len(data) - 1}개)")


def main():
    if not SPREADSHEET_ID:
        print("[ERROR] SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")
        return

    print(f"[sync] 매체마스터 자동 생성 시작")

    # 1. 포인트클릭_DB에서 unique media_name 추출
    media_names = extract_unique_media_names()

    if not media_names:
        print("[ERROR] 추출할 매체명이 없습니다.")
        return

    # 2. 매체마스터 시트 생성
    create_media_master(media_names)

    print(f"\n[완료] 매체마스터 생성 완료!")


if __name__ == "__main__":
    main()
