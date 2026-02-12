# GA4 데이터 수집 개선 완료

## 📌 변경 사항

### 기존 방식 (세션 중심)
- 날짜, 소스, 매체, 캠페인, 기기, 국가 등 기본 차원
- 세션 수, 사용자 수, 페이지 조회 등 기본 지표
- **문제점**: 구체적인 사용자 행동 분석 불가

### 새로운 방식 (이벤트/메뉴 중심) ✅
- **이벤트 추적**: 사용자가 어떤 행동을 했는지 (클릭, 조회, 구매 등)
- **메뉴/페이지 추적**: 어떤 화면에서 어떤 행동을 했는지
- **사용자 지표**: DAU/WAU/MAU로 활성 사용자 추적
- **커스텀 차원**: 버튼 ID, 탭 정보 등으로 세밀한 분석

---

## 🎯 새로 수집하는 데이터

### Dimensions (차원) - 8개

| 차원 | 설명 | 활용 |
|------|------|------|
| `date` | 날짜 | 일별 트렌드 분석 |
| `eventName` | 이벤트명 | 사용자 행동 추적 (로그인, 구매, 클릭 등) |
| `pageTitle` | 페이지 제목 | 화면별 방문 분석 |
| `pagePath` | 페이지 경로 | URL 패턴 분석 |
| `customEvent:*` | 커스텀 이벤트 | 메뉴/버튼 클릭, 탭 이동 추적 |
| `deviceCategory` | 기기 유형 | 모바일/데스크톱 비교 |

**커스텀 이벤트 차원:**
- **캐시플레이**: `page`, `page_type`, `button_id`
- **포인트클릭**: `page_name`, `page_type`, `tab`, `tab_title`, `tab_type`

### Metrics (지표) - 10개

| 지표 | 설명 | 활용 |
|------|------|------|
| `activeUsers` | 일별 활성 사용자 | **DAU** (Daily Active Users) |
| `active7DayUsers` | 7일 활성 사용자 | **WAU** (Weekly Active Users) |
| `active28DayUsers` | 28일 활성 사용자 | **MAU** (Monthly Active Users) |
| `newUsers` | 신규 사용자 | 신규 유입 추적 |
| `eventCount` | 이벤트 발생 횟수 | 클릭/조회 빈도 |
| `sessions` | 세션 수 | 방문 횟수 |
| `screenPageViews` | 페이지 조회수 | 화면 조회 |
| `averageSessionDuration` | 평균 세션 시간 (초) | 체류 시간 |
| `engagementRate` | 참여율 (%) | 사용자 참여도 |
| `userEngagementDuration` | 사용자 참여 시간 (초) | 총 체류 시간 |

---

## 📊 이제 분석 가능한 것들

### 1️⃣ DAU/WAU/MAU 분석
```python
# 날짜별 DAU/WAU/MAU
df.groupby('date').agg({
    'activeUsers': 'sum',      # DAU
    'active7DayUsers': 'sum',  # WAU
    'active28DayUsers': 'sum'  # MAU
})
```

### 2️⃣ 메뉴별 세션 시간
```python
# 어떤 메뉴에서 가장 오래 머무는지
df.groupby('pageTitle').agg({
    'averageSessionDuration': 'mean',
    'sessions': 'sum'
}).sort_values('averageSessionDuration', ascending=False)
```

### 3️⃣ 메뉴별 클릭수
```python
# 어떤 버튼이 가장 많이 클릭되는지
df[df['customEvent:button_id'].notna()].groupby('customEvent:button_id').agg({
    'eventCount': 'sum'
}).sort_values('eventCount', ascending=False)
```

### 4️⃣ 메뉴별 참여율
```python
# 어떤 메뉴에서 사용자가 가장 적극적인지
df.groupby('pageTitle').agg({
    'engagementRate': 'mean',
    'sessions': 'sum'
}).sort_values('engagementRate', ascending=False)
```

### 5️⃣ 이벤트별 분석
```python
# 특정 이벤트 발생 추이 (예: 구매)
df[df['eventName'] == 'purchase'].groupby('date').agg({
    'eventCount': 'sum',
    'activeUsers': 'sum'
})
```

---

## 🚀 다음 단계

### 1. 데이터 수집 테스트
GitHub Actions에서 워크플로우를 수동 실행하여 새 데이터 확인:
```
Actions → Sync CashPlay GA4 Data (또는 PointClick) → Run workflow
```

### 2. 대시보드 구현
`dashboards/cashplay.py`, `dashboards/pointclick.py`에 다음 섹션 추가:
- DAU/WAU/MAU 트렌드 차트
- 메뉴별 세션 시간 Top 10
- 이벤트별 발생 빈도
- 버튼별 클릭 순위
- 참여율 분석

### 3. 데이터 검증
- Google Sheets에서 새 데이터 확인
- `(not set)` 값 비율 확인
- 커스텀 차원 데이터 수집 확인

---

## 📚 참고 문서

- **GA4_DATA_ANALYSIS.md**: 데이터 분석 가이드 (쿼리 예제 포함)
- **GA4_GITHUB_ACTIONS.md**: GitHub Actions 설정 및 사용법
- **check_ga4_metadata.py**: GA4 메타데이터 조회 스크립트

---

## 🔄 자동 실행

- **스케줄**: 매일 오전 9시 (KST)
- **수집 기간**: 최근 90일
- **업데이트 방식**: 전체 덮어쓰기

---

## ✅ 완료된 작업

1. ✅ GA4 메타데이터 조회 (포인트클릭, 캐시플레이)
2. ✅ 이벤트 기반 데이터 수집으로 전환
3. ✅ DAU/WAU/MAU 지표 추가
4. ✅ 커스텀 이벤트 차원 추가
5. ✅ 데이터 분석 가이드 문서 작성
6. ✅ 변경사항 커밋

## 📝 남은 작업

1. ⏳ GitHub Actions 워크플로우 수동 실행 및 데이터 확인
2. ⏳ 대시보드에 새 데이터 반영 (시각화 추가)
3. ⏳ 데이터 검증 및 이상치 확인

---

## 💡 추가 정보

### 주요 이벤트 (캐시플레이 기준)
- `cp_install` - 앱 설치
- `cp_play` - 게임 플레이
- `game_detail` - 게임 상세 조회
- `login` - 로그인
- `purchase` - 구매
- `sign_up` - 회원가입
- `share` - 공유

### 커스텀 차원 활용 예시

**캐시플레이**:
- `customEvent:page`: 현재 페이지 이름
- `customEvent:page_type`: 페이지 유형
- `customEvent:button_id`: 클릭한 버튼 ID

**포인트클릭**:
- `customEvent:page_name`: 페이지 이름
- `customEvent:tab`: 탭 정보
- `customEvent:tab_title`: 탭 제목
- `customEvent:quest_*`: 퀘스트 관련 이벤트
- `customEvent:ad_*`: 광고 관련 이벤트

---

**변경 완료!** 이제 워크플로우를 실행하여 새 데이터를 수집해보세요 🎉
