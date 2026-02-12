# GA4 데이터 분석 가이드

## 📊 수집 데이터 구조

### 수집된 Dimensions (차원)

| 차원명 | 설명 | 활용 |
|-------|------|-----|
| `date` | 날짜 (YYYY-MM-DD) | 일별 트렌드 분석 |
| `eventName` | 이벤트명 | 사용자 행동 분석 (클릭, 조회 등) |
| `pageTitle` | 페이지 제목 | 화면별 방문 분석 |
| `pagePath` | 페이지 경로 | URL 패턴 분석 |
| `customEvent:page` | 커스텀 이벤트 - 페이지 | 특정 메뉴/화면 추적 |
| `customEvent:page_type` | 커스텀 이벤트 - 페이지 타입 | 페이지 유형별 분석 |
| `customEvent:button_id` | 커스텀 이벤트 - 버튼 ID | 버튼 클릭 추적 |
| `deviceCategory` | 기기 유형 | 모바일/데스크톱 비교 |

### 수집된 Metrics (지표)

| 지표명 | 설명 | 단위 | 활용 |
|-------|------|-----|-----|
| `activeUsers` | 일별 활성 사용자 | 명 | **DAU (Daily Active Users)** |
| `active7DayUsers` | 7일간 활성 사용자 | 명 | **WAU (Weekly Active Users)** |
| `active28DayUsers` | 28일간 활성 사용자 | 명 | **MAU (Monthly Active Users)** |
| `newUsers` | 신규 사용자 | 명 | 신규 유입 추적 |
| `eventCount` | 이벤트 발생 횟수 | 회 | 특정 행동 빈도 |
| `sessions` | 세션 수 | 회 | 방문 횟수 |
| `screenPageViews` | 화면 조회수 | 회 | 페이지 조회 |
| `averageSessionDuration` | 평균 세션 시간 | 초 | 체류 시간 |
| `engagementRate` | 참여율 | % | 사용자 참여도 |
| `userEngagementDuration` | 사용자 참여 시간 | 초 | 총 체류 시간 |

---

## 🎯 분석 시나리오

### 1️⃣ DAU/WAU/MAU 분석

**목적**: 일별/주간/월간 활성 사용자 추적

**쿼리 방법**:
```python
# 날짜별 DAU/WAU/MAU
df_dau = df_ga.groupby('date').agg({
    'activeUsers': 'sum',      # DAU
    'active7DayUsers': 'sum',  # WAU
    'active28DayUsers': 'sum'  # MAU
}).reset_index()
```

**활용**:
- DAU 트렌드 차트
- WAU/MAU 비율 (Stickiness 지표)
- 주간/월간 성장률

---

### 2️⃣ 메뉴별 세션 시간 분석

**목적**: 어떤 메뉴/화면에서 사용자가 가장 오래 머무는지

**쿼리 방법**:
```python
# 메뉴(pageTitle)별 평균 세션 시간
df_menu = df_ga.groupby('pageTitle').agg({
    'averageSessionDuration': 'mean',
    'sessions': 'sum',
    'activeUsers': 'sum'
}).reset_index()

# 체류 시간 내림차순 정렬
df_menu = df_menu.sort_values('averageSessionDuration', ascending=False)
```

**활용**:
- 인기 메뉴 파악
- 개선이 필요한 메뉴 식별 (체류 시간 짧은 경우)
- 메뉴별 사용자 수 비교

---

### 3️⃣ 메뉴별 클릭수 분석

**목적**: 어떤 버튼/메뉴가 가장 많이 클릭되는지

**쿼리 방법**:
```python
# 버튼별 클릭 횟수
df_clicks = df_ga[df_ga['customEvent:button_id'].notna()].groupby('customEvent:button_id').agg({
    'eventCount': 'sum',
    'activeUsers': 'nunique'
}).reset_index()

# 클릭 횟수 내림차순 정렬
df_clicks = df_clicks.sort_values('eventCount', ascending=False)
```

**활용**:
- 가장 많이 사용되는 기능 파악
- 버튼 배치 최적화
- 사용자 여정(User Journey) 분석

---

### 4️⃣ 메뉴별 참여율 분석

**목적**: 어떤 메뉴에서 사용자가 가장 적극적으로 참여하는지

**쿼리 방법**:
```python
# 메뉴(pageTitle)별 참여율
df_engagement = df_ga.groupby('pageTitle').agg({
    'engagementRate': 'mean',
    'sessions': 'sum',
    'eventCount': 'sum'
}).reset_index()

# 참여율 내림차순 정렬
df_engagement = df_engagement.sort_values('engagementRate', ascending=False)
```

**활용**:
- 참여도 높은 메뉴 파악
- 참여도 낮은 메뉴 개선
- 메뉴별 사용자 행동 비교

---

### 5️⃣ 이벤트별 분석

**목적**: 특정 사용자 행동(로그인, 구매, 공유 등) 추적

**쿼리 방법**:
```python
# 이벤트별 발생 횟수
df_events = df_ga.groupby(['date', 'eventName']).agg({
    'eventCount': 'sum',
    'activeUsers': 'sum'
}).reset_index()

# 특정 이벤트만 필터링 (예: 구매)
df_purchase = df_events[df_events['eventName'] == 'purchase']
```

**주요 이벤트** (CashPlay 기준):
- `cp_install` - 앱 설치
- `cp_play` - 게임 플레이
- `game_detail` - 게임 상세 조회
- `login` - 로그인
- `purchase` - 구매
- `sign_up` - 회원가입
- `share` - 공유
- `view_item` - 아이템 조회
- `view_item_list` - 목록 조회

**활용**:
- 전환율 분석 (설치 → 회원가입 → 구매)
- 이벤트 퍼널 분석
- 일별 이벤트 트렌드

---

### 6️⃣ 기기별 분석

**목적**: 모바일 vs 데스크톱 사용 패턴 비교

**쿼리 방법**:
```python
# 기기별 지표
df_device = df_ga.groupby('deviceCategory').agg({
    'activeUsers': 'sum',
    'sessions': 'sum',
    'averageSessionDuration': 'mean',
    'engagementRate': 'mean'
}).reset_index()
```

**활용**:
- 주요 사용 기기 파악
- 기기별 UX 최적화
- 반응형 디자인 우선순위

---

## 📈 추천 대시보드 구성

### 1. 개요 탭
- DAU/WAU/MAU 트렌드 차트
- 신규 사용자 vs 재방문 사용자
- 일별 세션 수

### 2. 메뉴 분석 탭
- 메뉴별 체류 시간 (Top 10)
- 메뉴별 방문 횟수
- 메뉴별 참여율

### 3. 클릭 분석 탭
- 버튼별 클릭 순위
- 클릭 히트맵 (일자별 × 버튼별)
- 사용자당 평균 클릭 수

### 4. 이벤트 분석 탭
- 주요 이벤트 발생 추이
- 이벤트 퍼널 (설치 → 로그인 → 구매)
- 이벤트별 전환율

---

## 🔄 데이터 업데이트

- **수집 주기**: 매일 오전 9시 (KST) 자동 실행
- **수집 기간**: 최근 90일
- **업데이트 방식**: 전체 덮어쓰기 (Replace)
- **시트명**: `포인트클릭_GA`, `캐시플레이_GA`

---

## 💡 분석 팁

### 1. (not set) 값 처리
GA4에서 일부 dimension이 수집되지 않은 경우 `(not set)` 또는 `(not provided)`로 표시됩니다.

```python
# (not set) 값 필터링
df_clean = df_ga[~df_ga['pageTitle'].str.contains('not set', case=False, na=False)]
```

### 2. 날짜 필터링
```python
# 최근 30일 데이터만
df_recent = df_ga[df_ga['date'] >= (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')]
```

### 3. 집계 함수 선택
- **sum**: 이벤트 카운트, 세션 수 등
- **mean**: 평균 세션 시간, 참여율 등
- **nunique**: 고유 사용자 수

### 4. 비율 계산
```python
# 이벤트 발생률
df_ga['event_rate'] = df_ga['eventCount'] / df_ga['sessions'] * 100
```

---

## 🎓 추가 학습 자료

- [GA4 Dimensions & Metrics 공식 문서](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema)
- [GA4 이벤트 추적 가이드](https://support.google.com/analytics/answer/9267735)
