"""
포인트클릭_DB 자동 적재 스크립트 (Supabase 버전)
- MySQL에서 전일자 데이터를 조회하여 Supabase pointclick_db 테이블에 upsert
- GitHub Actions에서 매일 오전 9시(KST) 실행
"""

import os
import sys
from datetime import datetime, date, timedelta, timezone

KST = timezone(timedelta(hours=9))
from decimal import Decimal

import pymysql
from supabase import create_client

# ============================================================
# 설정
# ============================================================
TABLE_NAME = "pointclick_db"

SQL_QUERY = """
SELECT
    rda.report_date as date,
    CASE WHEN rda.dsp_key = 0 THEN '직거래광고' ELSE '대행광고' END AS ad_category,
    m.media_type as media_type,
    COALESCE(p.publisher_type, '미지정') as publisher_type,
    a.ad_name as ad_name,
    m.media_name as media_name,
    a.ad_key as cd,
    a2.advertiser_name as advertiser,
    a.os_type as os,
    a.ad_type as ad_type,
    a.ad_cost as unit_price,
    SUM(rda.check_count) as clicks,
    SUM(rda.complete_count) as conversions,
    SUM(rda.cost_sum) as ad_revenue,
    SUM(rda.media_cost_sum) as media_cost,
    SUM(rda.media_cost_sum) / NULLIF(SUM(rda.cost_sum), 0) as media_rate,
    SUM(rda.cost_sum) - SUM(rda.media_cost_sum) as margin,
    (SUM(rda.cost_sum) - SUM(rda.media_cost_sum)) / NULLIF(SUM(rda.cost_sum), 0) as margin_rate,
    SUM(rda.complete_count) / NULLIF(SUM(rda.check_count), 0) as cvr,
    CONCAT(FLOOR((DAY(rda.report_date) - 1) / 7) + 1, '주차') AS week,
    DATE_FORMAT(rda.report_date, '%%y년 %%c월') AS month
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
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_supabase_client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def fetch_data_from_mysql(target_date: str) -> list[dict]:
    """MySQL에서 target_date 데이터를 조회하여 dict 리스트로 반환."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(SQL_QUERY, (target_date,))
            rows = cursor.fetchall()
    finally:
        conn.close()

    result = []
    for row in rows:
        formatted = {}
        for key, val in row.items():
            if val is None:
                formatted[key] = None
            elif isinstance(val, (datetime, date)):
                formatted[key] = val.strftime("%Y-%m-%d")
            elif isinstance(val, (float, Decimal)):
                f = round(float(val), 6)
                formatted[key] = int(f) if f == int(f) else f
            else:
                formatted[key] = val
        result.append(formatted)

    return result


def check_date_exists(client, target_date: str) -> bool:
    """Supabase 테이블에 해당 날짜 데이터가 이미 있는지 확인."""
    response = client.table(TABLE_NAME).select("date").eq("date", target_date).limit(1).execute()
    return len(response.data) > 0


def delete_date_data(client, target_date: str):
    """해당 날짜 데이터 삭제 (재적재를 위해)."""
    client.table(TABLE_NAME).delete().eq("date", target_date).execute()
    print(f"[sync] {target_date} 기존 데이터 삭제 완료")


def insert_to_supabase(client, rows: list[dict]) -> int:
    """Supabase에 데이터 일괄 삽입 (1000행 단위 청크)."""
    chunk_size = 1000
    total = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        client.table(TABLE_NAME).insert(chunk).execute()
        total += len(chunk)
        print(f"[sync] Supabase 삽입 중: {total}/{len(rows)}행")
    return total


def main():
    # 대상 날짜: 전일자 (또는 인자로 지정)
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        yesterday = datetime.now(KST) - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")

    print(f"[sync] 포인트클릭 DB 동기화 시작")
    print(f"[sync] 대상 날짜: {target_date}")

    client = get_supabase_client()

    # 1. 중복 체크
    if check_date_exists(client, target_date):
        print(f"[sync] {target_date} 데이터가 이미 존재합니다. 삭제 후 재적재합니다.")
        delete_date_data(client, target_date)

    # 2. MySQL에서 데이터 조회
    rows = fetch_data_from_mysql(target_date)

    if not rows:
        print(f"[sync] {target_date} 데이터가 MySQL에 없습니다.")
        return

    print(f"[sync] MySQL에서 {len(rows)}행 조회 완료")

    # 3. Supabase에 삽입
    count = insert_to_supabase(client, rows)
    print(f"[sync] Supabase {TABLE_NAME}에 {count}행 적재 완료")


if __name__ == "__main__":
    main()
