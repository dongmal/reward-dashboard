# GA4 자동 수집 - GitHub Actions 가이드

## ✅ 완료된 설정

### 1. 스크립트
- `sync_ga4_pointclick.py` - 포인트클릭 GA4 수집
- `sync_ga4_cashplay.py` - 캐시플레이 GA4 수집

### 2. GitHub Actions 워크플로우
- `.github/workflows/sync_ga4_pointclick.yml`
- `.github/workflows/sync_ga4_cashplay.yml`

**스케줄**: 매일 오전 9시 (KST) 자동 실행

---

## 🔑 필수 설정

### GitHub Secrets 등록

GitHub 저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

다음 2개의 Secrets를 추가하세요:

#### 1. GA4_POINTCLICK_PROPERTY_ID
```
Name: GA4_POINTCLICK_PROPERTY_ID
Value: properties/123456789
```
(포인트클릭 GA4 속성 ID로 변경)

#### 2. GA4_CASHPLAY_PROPERTY_ID
```
Name: GA4_CASHPLAY_PROPERTY_ID
Value: properties/987654321
```
(캐시플레이 GA4 속성 ID로 변경)

---

## 🔍 GA4 속성 ID 확인 방법

1. [Google Analytics](https://analytics.google.com/) 접속
2. **관리** (왼쪽 하단 톱니바퀴) 클릭
3. **속성 설정** 선택
4. **속성 ID** 확인 (예: `123456789`)
5. **앞에 `properties/`를 붙여서 등록**: `properties/123456789`

---

## 📊 수집 데이터

### Dimensions (차원)
- `date` - 날짜
- `sessionSource` - 소스
- `sessionMedium` - 매체
- `sessionCampaignName` - 캠페인명
- `deviceCategory` - 기기 유형
- `country` - 국가

### Metrics (지표)
- `sessions` - 세션 수
- `totalUsers` - 총 사용자 수
- `newUsers` - 신규 사용자 수
- `screenPageViews` - 페이지 조회수
- `eventCount` - 이벤트 수
- `conversions` - 전환 수
- `averageSessionDuration` - 평균 세션 시간 (초)
- `bounceRate` - 이탈률 (%)
- `engagementRate` - 참여율 (%)

### 수집 기간
- **기본**: 최근 90일
- **변경 가능**: 워크플로우 수동 실행 시 일수 지정

---

## ▶️ 사용 방법

### 1. 자동 실행 (권장)
GitHub Actions가 **매일 오전 9시 (KST)**에 자동으로 실행됩니다.
별도 작업 필요 없음!

### 2. 수동 실행
GitHub 저장소 → **Actions** 탭 → 워크플로우 선택 → **Run workflow**

**옵션:**
- `days` 파라미터: 수집 기간 (기본 90일)
  - 예: `30` 입력 시 최근 30일 데이터 수집

---

## 📝 동작 방식

```
1. GitHub Actions 실행 (매일 9시 또는 수동)
   ↓
2. GA4 API 호출 (최근 90일 데이터)
   ↓
3. 데이터 전처리
   - 날짜 포맷 변환
   - 비율 계산 (이탈률, 참여율)
   ↓
4. Google Sheets 업로드
   - 시트: 포인트클릭_GA, 캐시플레이_GA
   - 방식: 전체 삭제 후 새로 쓰기 (덮어쓰기)
   ↓
5. 대시보드 자동 반영
```

---

## 🔐 서비스 계정 권한

GA4 데이터를 읽으려면 서비스 계정에 권한이 필요합니다:

1. [Google Analytics](https://analytics.google.com/) 접속
2. **관리** → **속성 액세스 관리**
3. **+** 버튼 → 사용자 추가
4. **이메일**: GitHub Secrets의 `GCP_SERVICE_ACCOUNT` → `client_email` 값
5. **역할**: **뷰어** 선택
6. 추가 클릭

**포인트클릭과 캐시플레이 각각의 속성에 동일하게 적용**해야 합니다!

---

## ✅ 설정 확인

### 1. GitHub Actions 로그 확인
GitHub → **Actions** 탭 → 워크플로우 선택 → 최근 실행 로그

**성공 시:**
```
[sync] 포인트클릭 GA4 데이터 수집
[sync] 기간: 2024-01-01 ~ 2024-03-31 (90일)
[sync] Property ID: properties/123456789
[sync] GA4에서 1234행 조회 완료
[sync] Google Sheets에 1234행 적재 완료
```

**실패 시:**
```
[ERROR] GA4_POINTCLICK_PROPERTY_ID 환경변수가 설정되지 않았습니다.
```
→ GitHub Secrets 확인

### 2. Google Sheets 확인
스프레드시트에 `포인트클릭_GA`, `캐시플레이_GA` 시트 생성 확인

### 3. 대시보드 확인
대시보드 → 각 탭 하단 → "GA4 데이터" 섹션 표시

---

## 🛠️ 문제 해결

### "GA4_*_PROPERTY_ID 환경변수가 설정되지 않았습니다"
→ GitHub Secrets에 속성 ID 추가

### "권한이 없습니다" 에러
→ GA4 속성에 서비스 계정 뷰어 권한 부여

### "데이터가 없습니다"
→ GA4에 실제 데이터가 있는지 확인 또는 날짜 범위 조정

### 워크플로우가 실행되지 않음
→ GitHub Actions가 활성화되어 있는지 확인

---

## 📌 기존 DB 동기화와 비교

| 항목 | DB 동기화 | GA4 동기화 |
|-----|----------|-----------|
| 소스 | MySQL | Google Analytics |
| 방식 | Append (추가) | Replace (덮어쓰기) |
| 기간 | 전일자 (1일) | 최근 90일 |
| 스케줄 | 매일 9시 | 매일 9시 |
| 중복 체크 | O | X (전체 덮어쓰기) |

---

## 🎯 요약

1. **GitHub Secrets 등록** (1회만)
   - `GA4_POINTCLICK_PROPERTY_ID`
   - `GA4_CASHPLAY_PROPERTY_ID`

2. **서비스 계정 권한 부여** (1회만)
   - 각 GA4 속성에 뷰어 권한

3. **자동 실행**
   - 매일 오전 9시 자동 수집
   - 별도 작업 불필요

끝! 🎉
