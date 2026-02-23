"""
GA4 API에서 사용 가능한 모든 측정기준(Dimensions)과 측정항목(Metrics) 조회
"""

import os
import json
import sys

from google.oauth2.service_account import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import GetMetadataRequest


def get_ga4_metadata(property_id: str):
    """GA4 속성의 사용 가능한 모든 측정기준과 측정항목 조회"""

    # 환경변수에서 자격증명 로드
    try:
        creds_json = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
    except KeyError:
        print("❌ GCP_SERVICE_ACCOUNT 환경변수가 설정되지 않았습니다.")
        print("GitHub Actions나 터미널에서 환경변수를 설정하고 실행하세요.")
        sys.exit(1)

    scopes = ["https://www.googleapis.com/auth/analytics.readonly"]
    credentials = Credentials.from_service_account_info(creds_json, scopes=scopes)

    # GA4 클라이언트 생성
    client = BetaAnalyticsDataClient(credentials=credentials)

    # 메타데이터 요청
    request = GetMetadataRequest(name=f"{property_id}/metadata")
    response = client.get_metadata(request)

    # 측정기준(Dimensions) 정리
    print("\n" + "=" * 100)
    print("📏 측정기준 (Dimensions)")
    print("=" * 100)

    dimensions = {}
    for dim in response.dimensions:
        category = dim.category or "기타"
        if category not in dimensions:
            dimensions[category] = []
        dimensions[category].append({
            'api_name': dim.api_name,
            'ui_name': dim.ui_name,
            'description': dim.description
        })

    for category, items in sorted(dimensions.items()):
        print(f"\n📂 {category}")
        print("-" * 100)
        for item in sorted(items, key=lambda x: x['api_name']):
            print(f"  • {item['api_name']:40s} | {item['ui_name']:30s} | {item['description'][:50]}")

    # 측정항목(Metrics) 정리
    print("\n\n" + "=" * 100)
    print("📊 측정항목 (Metrics)")
    print("=" * 100)

    metrics = {}
    for metric in response.metrics:
        category = metric.category or "기타"
        if category not in metrics:
            metrics[category] = []
        metrics[category].append({
            'api_name': metric.api_name,
            'ui_name': metric.ui_name,
            'description': metric.description,
            'type': metric.type_.name if hasattr(metric, 'type_') else 'UNKNOWN'
        })

    for category, items in sorted(metrics.items()):
        print(f"\n📂 {category}")
        print("-" * 100)
        for item in sorted(items, key=lambda x: x['api_name']):
            type_str = f"[{item['type']}]"
            print(f"  • {item['api_name']:40s} | {item['ui_name']:30s} | {type_str:15s} | {item['description'][:40]}")

    # 통계
    print("\n\n" + "=" * 100)
    print("📈 요약")
    print("=" * 100)
    print(f"총 측정기준: {len(response.dimensions)}개")
    print(f"총 측정항목: {len(response.metrics)}개")

    # 유용한 조합 추천
    print("\n\n" + "=" * 100)
    print("💡 추천 조합 (메뉴/이벤트 분석용)")
    print("=" * 100)

    print("\n1️⃣ 이벤트별 분석:")
    print("   Dimensions: date, eventName")
    print("   Metrics: eventCount, totalUsers, sessions, averageSessionDuration")

    print("\n2️⃣ 화면/페이지별 분석:")
    print("   Dimensions: date, pageTitle, pagePath")
    print("   Metrics: screenPageViews, totalUsers, sessions, averageSessionDuration")

    print("\n3️⃣ 사용자 지표 (DAU/MAU):")
    print("   Dimensions: date")
    print("   Metrics: activeUsers (DAU), newUsers, totalUsers")

    print("\n4️⃣ 메뉴 클릭/참여:")
    print("   Dimensions: date, eventName, linkUrl, linkText")
    print("   Metrics: eventCount, engagementRate, sessions")

    print("\n" + "=" * 100)


def main():
    # 포인트클릭 또는 캐시플레이 선택
    if len(sys.argv) < 2:
        print("사용법: python check_ga4_metadata.py [pointclick|cashplay]")
        print("예: python check_ga4_metadata.py pointclick")
        sys.exit(1)

    service = sys.argv[1].lower()

    if service == "pointclick":
        property_id = os.environ.get("GA4_POINTCLICK_PROPERTY_ID")
        name = "포인트클릭"
    elif service == "cashplay":
        property_id = os.environ.get("GA4_CASHPLAY_PROPERTY_ID")
        name = "캐시플레이"
    else:
        print(f"❌ 잘못된 서비스명: {service}")
        print("pointclick 또는 cashplay를 입력하세요.")
        sys.exit(1)

    if not property_id:
        print(f"❌ GA4_{service.upper()}_PROPERTY_ID 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    print(f"\n🔍 {name} GA4 메타데이터 조회 중...")
    print(f"Property ID: {property_id}")

    get_ga4_metadata(property_id)


if __name__ == "__main__":
    main()
