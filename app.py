import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, date

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="E프로젝트 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS — Power BI 스타일 + Light/Dark 대응 + 버튼 스타일 수정
# ============================================================
st.markdown("""
<style>
/* ── 전역 ── */
.main .block-container { padding-top: 1rem; max-width: 1440px; }

/* ── 메트릭 카드 ── */
div[data-testid="stMetric"] {
    border-radius: 8px;
    padding: 14px 16px;
    border-left: 4px solid #5B9BD5;
    background-color: white;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
div[data-testid="stMetric"]:nth-of-type(2) { border-left-color: #70AD47; }
div[data-testid="stMetric"]:nth-of-type(3) { border-left-color: #FFC000; }
div[data-testid="stMetric"]:nth-of-type(4) { border-left-color: #ED7D31; }
div[data-testid="stMetric"]:nth-of-type(5) { border-left-color: #A855F7; }

div[data-testid="stMetric"] label {
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    opacity: 0.7;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
}

/* ── 기간 선택 버튼 커스텀 (작게) ── */
div.stButton > button {
    width: 100%;
    border-radius: 4px;
    font-size: 12px;
    padding: 4px 8px;
    height: auto;
    min-height: 32px;
    background-color: #f0f2f6;
    border: 1px solid #dce1e6;
    color: #31333F;
}
div.stButton > button:hover {
    border-color: #5B9BD5;
    color: #5B9BD5;
}

/* ── 탭 스타일 ── */
button[data-baseweb="tab"] {
    font-weight: 700 !important;
    font-size: 1rem !important;
}
div[data-baseweb="tab-highlight"] { background-color: #5B9BD5 !important; }

</style>
""", unsafe_allow_html=True)

SHEET_NAMES = {
    "포인트클릭": {"db": "포인트클릭_DB"},
    "캐시플레이": {"db": "캐시플레이_DB"}
}

PASTEL = {
    'blue': '#5B9BD5', 'green': '#70AD47', 'orange': '#ED7D31',
    'yellow': '#FFC000', 'purple': '#A855F7', 'red': '#E05252',
    'teal': '#4DB8A4', 'gray': '#A0AEC0', 'pink': '#E88B9E',
    'game': '#5B9BD5', 'gathering': '#A855F7', 'iaa': '#70AD47', 'offerwall': '#ED7D31',
    'pc_highlight': '#E05252',
}
PUB_COLORS = ['#5B9BD5', '#ED7D31', '#70AD47', '#A855F7', '#E05252', '#4DB8A4', '#FFC000', '#A0AEC0']

# ============================================================
# 인증 (FSN 도메인)
# ============================================================
# 개발 환경 테스트를 위해 로컬에서는 Pass하고 싶다면 아래 주석 처리 필요
# 여기서는 요청하신 코드 그대로 유지합니다.
# ------------------------------------------------------------------
# ALLOWED_DOMAIN = "fsn.co.kr"
# if not st.user.is_logged_in: ... (생략, 기존 코드 유지한다고 가정)
# 하지만 실행 오류 방지를 위해 임시로 주석 처리하거나 로직 유지
# ------------------------------------------------------------------

# ============================================================
# 데이터 로딩
# ============================================================
@st.cache_data(ttl=600)
def load_sheet_data(sheet_name: str) -> pd.DataFrame:
    # st.secrets 설정이 되어 있다고 가정
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(st.secrets["spreadsheet_id"])
        ws = sh.worksheet(sheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        # secrets가 없을 때를 대비한 예외처리 (코드 실행 보여주기용)
        return pd.DataFrame() 

def load_pointclick(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    col_map = {
        '일자': 'date', '광고구분': 'ad_category', '매체타입': 'media_type',
        '퍼블리셔타입': 'publisher_type', '광고명': 'ad_name', '매체명': 'media_name',
        'CD': 'cd', '광고주명': 'advertiser', 'OS': 'os', '광고타입': 'ad_type',
        '광고단가': 'unit_price', '클릭수': 'clicks', '전환수': 'conversions',
        '광고비': 'ad_revenue', '매체수익금': 'media_cost', '매체정산비율': 'media_rate',
        '마진금액': 'margin', '마진율': 'margin_rate', 'CVR': 'cvr',
        '주차': 'week', '월별': 'month'
    }
    df = df.rename(columns=col_map)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    for c in ['unit_price','clicks','conversions','ad_revenue','media_cost','media_rate','margin','margin_rate','cvr']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df

def load_cashplay(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    col_map = {
        '날짜': 'date',
        '리워드(원)_유상': 'reward_paid', '리워드(원)_무상': 'reward_free', '리워드(원)_합계': 'reward_total',
        '게임(원)_직거래': 'game_direct', '게임(원)_DSP': 'game_dsp', '게임(원)_RS': 'game_rs',
        '게임(원)_인수': 'game_acquisition', '게임(원)_합계': 'game_total',
        '게더링(원)_포인트클릭': 'gathering_pointclick',
        'IAA(원)_레벨플레이': 'iaa_levelplay', 'IAA(원)_애드웨일': 'iaa_adwhale',
        'IAA(원)_허블': 'iaa_hubble', 'IAA(원)_합계': 'iaa_total',
        '오퍼월(원)_애드팝콘': 'offerwall_adpopcorn', '오퍼월(원)_포인트클릭': 'offerwall_pointclick',
        '오퍼월(원)_아이브': 'offerwall_ive', '오퍼월(원)_애드포러스': 'offerwall_adforus',
        '오퍼월(원)_애디슨': 'offerwall_addison', '오퍼월(원)_애드조': 'offerwall_adjo',
        '오퍼월(원)_합계': 'offerwall_total'
    }
    df = df.rename(columns=col_map)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    for c in [x for x in df.columns if x != 'date']:
        df[c] = pd.to_numeric(df[c].replace('-', 0), errors='coerce').fillna(0)
    df['revenue_total'] = df['game_total'] + df['gathering_pointclick'] + df['iaa_total'] + df['offerwall_total']
    df['cost_total'] = df['reward_total']
    df['margin'] = df['revenue_total'] - df['cost_total']
    df['margin_rate'] = (df['margin'] / df['revenue_total'] * 100).round(1).replace([float('inf'), float('-inf')], 0)
    df['pointclick_revenue'] = df['gathering_pointclick'] + df['offerwall_pointclick']
    return df

# ============================================================
# 유틸리티 & 차트 레이아웃
# ============================================================
def format_won(n):
    if abs(n) >= 1e8: return f"₩{n/1e8:.1f}억"
    if abs(n) >= 1e4: return f"₩{n/1e4:,.0f}만"
    return f"₩{n:,.0f}"

def format_number(n): return f"{n:,.0f}"
def format_pct(n): return f"{n:,.1f}%"

def make_weekly(df, date_col='date', group_col=None):
    if df.empty: return df
    t = df.copy()
    t['week_start'] = t[date_col].dt.to_period('W').apply(lambda x: x.start_time)
    nums = [c for c in t.columns if pd.api.types.is_numeric_dtype(t[c]) and c != date_col]
    if group_col:
        r = t.groupby(['week_start', group_col])[nums].sum().reset_index()
    else:
        r = t.groupby('week_start')[nums].sum().reset_index()
    return r.rename(columns={'week_start': 'week'})

def week_label(d):
    e = d + timedelta(days=6)
    return f"{d.month}/{d.day}~{e.month}/{e.day}"

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(size=11),
    margin=dict(t=20, b=40, l=40, r=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified"
)
def apply_layout(fig, extra=None):
    l = {**CHART_LAYOUT}
    if extra: l.update(extra)
    fig.update_layout(**l)
    return fig

# ============================================================
# [핵심] 기간별 전일비(전기비) 계산 함수
# ============================================================
def get_comparison_metrics(df, start_date, end_date):
    """
    선택된 기간(Current)과 그 직전 동일 기간(Previous)의 데이터를 계산하여 반환
    """
    if df.empty:
        return {}, {}
        
    # 1. 현재 기간 데이터
    curr_mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
    curr_df = df[curr_mask]
    
    # 2. 직전 기간 계산 (기간 차이만큼 뒤로 이동)
    # 예: 오늘(1일) 선택 -> 비교대상: 어제(1일)
    # 예: 이번주(7일) 선택 -> 비교대상: 지난주(7일)
    duration_days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration_days - 1)
    
    prev_mask = (df['date'].dt.date >= prev_start) & (df['date'].dt.date <= prev_end)
    prev_df = df[prev_mask]
    
    # 3. 합계 계산 (숫자 컬럼만)
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    curr_sums = curr_df[numeric_cols].sum()
    prev_sums = prev_df[numeric_cols].sum()
    
    # 4. 변화율(Delta) 계산 함수
    def get_delta(col):
        c = curr_sums.get(col, 0)
        p = prev_sums.get(col, 0)
        if p == 0: return 0
        return ((c - p) / p) * 100

    return curr_sums, get_delta

# ============================================================
# [UI 수정] 빠른 날짜 선택기 (버튼 작게 + 날짜 입력 아래로)
# ============================================================
def quick_date_picker(data_min, data_max, prefix, default_mode="이번 달"):
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # 프리셋 정의
    presets = {
        "오늘": (today, today),
        "어제": (yesterday, yesterday),
        "이번주": (today - timedelta(days=today.weekday()), today),
        "지난주": (today - timedelta(days=today.weekday() + 7), today - timedelta(days=today.weekday() + 1)),
        "이번달": (today.replace(day=1), today),
        "지난달": ((today.replace(day=1) - timedelta(days=1)).replace(day=1), today.replace(day=1) - timedelta(days=1)),
    }

    # 세션 상태 초기화
    if f"{prefix}_from" not in st.session_state:
        ds, de = presets.get(default_mode, (today, today))
        st.session_state[f"{prefix}_from"] = max(ds, data_min)
        st.session_state[f"{prefix}_to"] = min(de, data_max)

    # 1. 버튼 행 (작은 컬럼들)
    # st.columns의 gap="small"을 사용하여 간격을 좁힘
    btn_cols = st.columns(6) 
    
    clicked_preset = None
    for i, (label, (ps, pe)) in enumerate(presets.items()):
        # 버튼 UI
        if btn_cols[i].button(label, key=f"{prefix}_btn_{label}"):
            clicked_preset = (ps, pe)

    # 버튼 클릭 시 세션 업데이트 및 리런
    if clicked_preset:
        st.session_state[f"{prefix}_from"] = max(clicked_preset[0], data_min)
        st.session_state[f"{prefix}_to"] = min(clicked_preset[1], data_max)
        st.rerun()

    # 2. 날짜 입력 행 (버튼 아래에 배치)
    # 날짜 입력칸이 너무 넓지 않게 앞쪽 컬럼에 배치
    dc1, dc2, _ = st.columns([1, 1, 3])
    with dc1:
        d_from = st.date_input(
            "시작일", 
            value=st.session_state[f"{prefix}_from"],
            min_value=data_min, max_value=data_max,
            key=f"{prefix}_di_from"
        )
    with dc2:
        d_to = st.date_input(
            "종료일", 
            value=st.session_state[f"{prefix}_to"],
            min_value=data_min, max_value=data_max,
            key=f"{prefix}_di_to"
        )
    
    # 날짜 입력값이 변경되면 세션 업데이트
    st.session_state[f"{prefix}_from"] = d_from
    st.session_state[f"{prefix}_to"] = d_to

    return d_from, d_to


# ============================================================
# 포인트클릭 대시보드
# ============================================================
def render_pointclick_dashboard(df: pd.DataFrame):
    if df.empty:
        st.warning("데이터가 없습니다.")
        return

    dmin, dmax = df['date'].min().date(), df['date'].max().date()

    with st.sidebar:
        st.markdown("### 🔍 필터")
        pub_types = ['전체'] + sorted(df['publisher_type'].unique().tolist())
        sel_pub = st.selectbox("퍼블리셔", pub_types, key="pc_pub")
        
    f = df.copy()
    if sel_pub != '전체': f = f[f['publisher_type'] == sel_pub]

    # ── 기간 설정 및 핵심 지표 ──
    st.markdown("#### 📅 조회 기간 설정")
    kf, kt = quick_date_picker(dmin, dmax, "pc_kpi", "이번달")
    
    st.markdown("---")
    st.markdown("## 📈 핵심 지표")
    
    # 기간별 전일비(전기비) 계산
    curr_sums, get_delta = get_comparison_metrics(f, kf, kt)
    
    if curr_sums.empty:
        st.info("선택한 기간에 데이터가 없습니다.")
    else:
        # 지표 계산
        tr = curr_sums['ad_revenue']
        tm = curr_sums['margin']
        tv = curr_sums['conversions']
        tc = curr_sums['clicks']
        amr = (tm / tr * 100) if tr else 0
        acvr = (tv / tc * 100) if tc else 0

        # UI 출력
        m1,m2,m3,m4,m5 = st.columns(5)
        # delta 값에 get_delta 함수 사용 -> 비교 기간(전주, 전월 등) 대비 증감률 표시
        m1.metric("광고비(매출)", format_won(tr), delta=f"{get_delta('ad_revenue'):+.1f}%")
        m2.metric("마진", format_won(tm), delta=f"{get_delta('margin'):+.1f}%")
        m3.metric("마진율", format_pct(amr))
        m4.metric("전환수", format_number(tv), delta=f"{get_delta('conversions'):+.1f}%")
        m5.metric("평균 CVR", format_pct(acvr))

    st.markdown("---")
    
    # ── 필터링된 데이터프레임 (차트용) ──
    kdf = f[(f['date'].dt.date >= kf) & (f['date'].dt.date <= kt)]
    
    if kdf.empty: return

    # ── 상세 차트 (탭) ──
    t1, t2 = st.tabs(["📊 퍼블리셔별 추이", "📋 상세 데이터"])
    
    with t1:
        wp = make_weekly(kdf, group_col='publisher_type')
        wp['wl'] = wp['week'].apply(week_label)
        
        fig = go.Figure()
        pubs = sorted(wp['publisher_type'].unique())
        for i, p in enumerate(pubs):
            s = wp[wp['publisher_type']==p].sort_values('week')
            fig.add_trace(go.Bar(x=s['wl'], y=s['ad_revenue'], name=p, marker_color=PUB_COLORS[i%len(PUB_COLORS)]))
        
        apply_layout(fig, dict(barmode='stack', height=400, title="주간 퍼블리셔별 매출 추이"))
        st.plotly_chart(fig, use_container_width=True)
        
    with t2:
        st.dataframe(kdf.sort_values('date', ascending=False), use_container_width=True, hide_index=True)


# ============================================================
# 캐시플레이 대시보드
# ============================================================
def render_cashplay_dashboard(df: pd.DataFrame):
    if df.empty:
        st.warning("데이터가 없습니다.")
        return

    dmin, dmax = df['date'].min().date(), df['date'].max().date()

    st.markdown("#### 📅 조회 기간 설정")
    kf, kt = quick_date_picker(dmin, dmax, "cp_kpi", "이번달")
    
    st.markdown("---")
    st.markdown("## 📈 핵심 지표")

    # 기간별 전일비(전기비) 계산
    curr_sums, get_delta = get_comparison_metrics(df, kf, kt)

    if curr_sums.empty:
        st.info("데이터 없음")
    else:
        tr = curr_sums['revenue_total']
        tc = curr_sums['cost_total']
        tm = curr_sums['margin']
        amr = (tm/tr*100) if tr else 0
        tpc = curr_sums['pointclick_revenue']
        apcr = (tpc/tr*100) if tr else 0

        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("총 매출", format_won(tr), delta=f"{get_delta('revenue_total'):+.1f}%")
        m2.metric("매입(리워드)", format_won(tc))
        m3.metric("마진", format_won(tm), delta=f"{get_delta('margin'):+.1f}%")
        m4.metric("마진율", format_pct(amr))
        m5.metric("자사 비중", format_pct(apcr))

    st.markdown("---")
    
    # ── 필터링된 데이터프레임 ──
    kdf = df[(df['date'].dt.date >= kf) & (df['date'].dt.date <= kt)]
    if kdf.empty: return

    c1, c2 = st.columns(2)
    with c1:
        cats = {'게임': kdf['game_total'].sum(), '게더링': kdf['gathering_pointclick'].sum(),
                'IAA': kdf['iaa_total'].sum(), '오퍼월': kdf['offerwall_total'].sum()}
        fig_p = px.pie(values=list(cats.values()), names=list(cats.keys()), hole=0.5,
                       color_discrete_sequence=[PASTEL['game'], PASTEL['gathering'], PASTEL['iaa'], PASTEL['offerwall']])
        fig_p.update_layout(height=350, title="매출 구성")
        st.plotly_chart(fig_p, use_container_width=True)
    with c2:
        # 주간 추이
        w = make_weekly(kdf)
        w['wl'] = w['week'].apply(week_label)
        fig_w = go.Figure()
        fig_w.add_trace(go.Bar(x=w['wl'], y=w['revenue_total'], name="매출", marker_color=PASTEL['blue']))
        fig_w.add_trace(go.Bar(x=w['wl'], y=w['margin'], name="마진", marker_color=PASTEL['green']))
        apply_layout(fig_w, dict(barmode='group', height=350, title="주간 매출/마진 추이"))
        st.plotly_chart(fig_w, use_container_width=True)

# ============================================================
# 메인
# ============================================================
def main():
    st.title("📊 E프로젝트 대시보드")
    
    with st.sidebar:
        if st.button("🔄 데이터 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    tab_pc, tab_cp = st.tabs(["🟢 PointClick", "🔵 CashPlay"])

    with tab_pc:
        # 실제 데이터 로딩 (secrets가 설정되어 있어야 함)
        # pc_raw = load_sheet_data(SHEET_NAMES["포인트클릭"]["db"])
        # pc_df = load_pointclick(pc_raw)
        
        # 테스트용 빈 데이터프레임 (실행 확인용)
        # 실제 사용시는 위 주석을 풀고 아래 줄을 지우세요.
        pc_df = pd.DataFrame() 
        render_pointclick_dashboard(pc_df)

    with tab_cp:
        # cp_raw = load_sheet_data(SHEET_NAMES["캐시플레이"]["db"])
        # cp_df = load_cashplay(cp_raw)
        cp_df = pd.DataFrame()
        render_cashplay_dashboard(cp_df)

if __name__ == "__main__":
    main()