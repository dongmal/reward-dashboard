# GA4 데이터 자동 수집 설정 가이드

## 1. GA4 Property ID 확인

1. [Google Analytics](https://analytics.google.com/) 접속
2. 관리 → 속성 설정 → 속성 세부정보
3. **속성 ID** 확인 (숫자만, 예: `123456789`)

포인트클릭과 캐시플레이 각각의 속성 ID를 확인하세요.

## 2. Secrets 설정

`.streamlit/secrets.toml` 파일에 다음 내용을 추가하세요:

```toml
# GA4 속성 ID (properties/ 접두사 포함)
ga4_pointclick_property_id = "properties/123456789"  # 포인트클릭 속성 ID
ga4_cashplay_property_id = "properties/987654321"    # 캐시플레이 속성 ID
```

**주의**: `properties/` 접두사를 꼭 포함해야 합니다!

## 3. 서비스 계정 권한 설정

Google Cloud Console에서 서비스 계정에 GA4 읽기 권한을 부여해야 합니다:

1. [Google Analytics](https://analytics.google.com/) 접속
2. 관리 → 속성 → 속성 액세스 관리
3. 서비스 계정 이메일 추가 (secrets.toml의 `client_email`)
4. **뷰어** 역할 부여

포인트클릭과 캐시플레이 각각의 속성에 동일한 서비스 계정을 추가하세요.

## 4. 수집할 데이터

각 스크립트는 다음 데이터를 수집합니다:

### Dimensions (차원)
- `date`: 날짜
- `sessionSource`: 소스
- `sessionMedium`: 매체
- `sessionCampaignName`: 캠페인명
- `deviceCategory`: 기기 유형
- `country`: 국가

### Metrics (측정항목)
- `sessions`: 세션 수
- `totalUsers`: 총 사용자 수
- `newUsers`: 신규 사용자 수
- `screenPageViews`: 페이지 조회수
- `eventCount`: 이벤트 수
- `conversions`: 전환 수
- `averageSessionDuration`: 평균 세션 시간
- `bounceRate`: 이탈률 (%)
- `engagementRate`: 참여율 (%)

### 수집 기간
- 기본: 최근 90일
- 스크립트 수정으로 변경 가능

## 5. 실행 방법

### 개별 실행
```bash
# 포인트클릭만
streamlit run sync_ga4_pointclick.py

# 캐시플레이만
streamlit run sync_ga4_cashplay.py
```

### 일괄 실행
```bash
python sync_ga4_all.py
```

## 6. 자동화 (선택사항)

### Windows 작업 스케줄러
1. 작업 스케줄러 열기
2. 기본 작업 만들기
3. 동작: `python C:\path\to\sync_ga4_all.py`
4. 트리거: 매일 오전 6시

### Linux/Mac cron
```bash
# crontab -e
0 6 * * * cd /path/to/project && python sync_ga4_all.py
```

## 7. 문제 해결

### "ga4_pointclick_property_id가 설정되지 않았습니다"
→ `.streamlit/secrets.toml`에 속성 ID 추가

### "권한이 없습니다" 에러
→ GA4 속성에 서비스 계정 추가 및 뷰어 권한 부여

### "데이터가 없습니다"
→ 날짜 범위 확인 또는 GA4에 실제 데이터가 있는지 확인

## 8. 수집 결과 확인

수집이 완료되면 Google Sheets에 다음 시트가 생성됩니다:
- `포인트클릭_GA`
- `캐시플레이_GA`

대시보드를 새로고침하면 GA4 데이터 섹션에 표시됩니다.
