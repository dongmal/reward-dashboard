# GA4 환경별 설정 가이드

## 🔧 설정이 필요한 값

다음 2개의 GA4 속성 ID가 필요합니다:

```
ga4_pointclick_property_id = "properties/123456789"
ga4_cashplay_property_id = "properties/987654321"
```

**속성 ID 확인 방법:**
1. [Google Analytics](https://analytics.google.com/) 접속
2. 관리 → 속성 설정 → 속성 세부정보
3. **속성 ID** 확인 (예: `123456789`)
4. `properties/` 접두사를 붙여서 사용: `properties/123456789`

---

## 📍 환경별 설정 방법

### 1️⃣ Streamlit Community Cloud (배포 환경)

**웹 UI에서 설정:**

1. [Streamlit Cloud](https://share.streamlit.io/) 접속
2. 앱 선택 → ⚙️ Settings → Secrets
3. 아래 내용을 **추가** (기존 내용 유지하고 아래만 추가):

```toml
# GA4 속성 ID
ga4_pointclick_property_id = "properties/123456789"
ga4_cashplay_property_id = "properties/987654321"
```

4. Save 클릭
5. 앱 자동 재시작됨

**⚠️ 주의:**
- 기존의 `gcp_service_account`, `spreadsheet_id` 등은 **절대 삭제하지 마세요!**
- 위 2줄만 **맨 아래에 추가**하면 됩니다.

---

### 2️⃣ 로컬 환경 (테스트용)

**파일 생성:**

프로젝트 루트에 `.streamlit` 폴더를 만들고 `secrets.toml` 파일 생성:

```bash
# Windows
mkdir .streamlit
notepad .streamlit\secrets.toml

# Mac/Linux
mkdir .streamlit
nano .streamlit/secrets.toml
```

**파일 내용:**

```toml
# GCP 서비스 계정 (기존 설정)
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."

# Google Sheets ID (기존 설정)
spreadsheet_id = "your-spreadsheet-id"

# GA4 속성 ID (신규 추가)
ga4_pointclick_property_id = "properties/123456789"
ga4_cashplay_property_id = "properties/987654321"
```

---

### 3️⃣ GitHub Codespaces / Cloud IDE

GitHub Codespaces나 다른 클라우드 IDE를 사용하는 경우:

**방법 1: Secrets 기능 사용 (추천)**
- GitHub Codespaces → Settings → Secrets
- `GA4_POINTCLICK_PROPERTY_ID` 추가
- `GA4_CASHPLAY_PROPERTY_ID` 추가

**방법 2: 환경 변수**
```bash
export GA4_POINTCLICK_PROPERTY_ID="properties/123456789"
export GA4_CASHPLAY_PROPERTY_ID="properties/987654321"
```

그러나 이 경우 스크립트 수정이 필요합니다.

---

## ✅ 설정 확인 방법

설정이 제대로 되었는지 확인하려면:

**방법 1: Python으로 확인**
```python
import streamlit as st

# 이 코드를 임시로 app.py에 추가해서 확인
print("포인트클릭 GA4:", st.secrets.get("ga4_pointclick_property_id", "❌ 없음"))
print("캐시플레이 GA4:", st.secrets.get("ga4_cashplay_property_id", "❌ 없음"))
```

**방법 2: 스크립트 실행**
```bash
streamlit run sync_ga4_pointclick.py
```

- "❌ ga4_pointclick_property_id가 설정되지 않았습니다" → 설정 필요
- "📊 포인트클릭 GA4 데이터 수집 시작" → 설정 완료

---

## 🔐 보안 참고사항

1. **절대 GitHub에 업로드하지 마세요:**
   - `.streamlit/secrets.toml`은 `.gitignore`에 포함되어 있어야 함
   - 이미 `.gitignore`에 추가되어 있는지 확인

2. **서비스 계정 권한:**
   - GA4 속성별로 서비스 계정에 "뷰어" 권한 부여 필요
   - Google Analytics → 관리 → 속성 액세스 관리

---

## 🎯 요약

**가장 간단한 방법 (배포 환경):**

Streamlit Cloud 웹 UI → Settings → Secrets에 추가:
```toml
ga4_pointclick_property_id = "properties/123456789"
ga4_cashplay_property_id = "properties/987654321"
```

이게 전부입니다! 👍
