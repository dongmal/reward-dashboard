"""
매체마스터 자동 생성 스크립트 (Supabase 버전)
- MySQL media 테이블에서 media_key, media_name 직접 조회
- Supabase media_master 테이블에 upsert
"""

import os
import sys
import pymysql
from supabase import create_client

TABLE_NAME = "media_master"
SQL_QUERY = "SELECT media_key, media_name FROM media ORDER BY media_key"


def get_mysql_connection():
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ.get("MYSQL_PORT", 3306)),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_supabase_client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def fetch_media_from_mysql() -> list:
    """MySQL media 테이블에서 media_key, media_name 조회"""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(SQL_QUERY)
            rows = cursor.fetchall()
    finally:
        conn.close()

    result = []
    for row in rows:
        result.append({
            "media_key": str(row["media_key"]),
            "media_name": str(row["media_name"]) if row["media_name"] else ""
        })

    print(f"[sync] MySQL에서 {len(result)}개 매체 조회 완료")
    return result


def main():
    print(f"[sync] 매체마스터 자동 생성 시작")

    rows = fetch_media_from_mysql()

    if not rows:
        print("[ERROR] MySQL media 테이블에 데이터가 없습니다.")
        return

    client = get_supabase_client()

    # upsert: media_key 기준으로 insert or update
    chunk_size = 500
    total = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        client.table(TABLE_NAME).upsert(chunk, on_conflict="media_key").execute()
        total += len(chunk)

    print(f"[sync] Supabase {TABLE_NAME}에 {total}개 매체 upsert 완료")

    # 샘플 출력
    print("\n[샘플 데이터]")
    for row in rows[:5]:
        print(f"  {row['media_key']:20} | {row['media_name']}")
    if len(rows) > 5:
        print(f"  ... (총 {len(rows)}개)")

    print(f"\n[완료] 매체마스터 생성 완료!")


if __name__ == "__main__":
    main()
