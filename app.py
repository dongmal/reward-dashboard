import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, date
import numpy as np
from functools import wraps

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
# CSS – Power BI 스타일 + Light/Dark 대응
# ============================================================
st.markdown("""
<style>
.main .block-container { padding-top: 1rem; max-width: 1440px; }
div[data-testid="stMetric"] {
    border-radius: 8px; padding: 14px 16px; border-left: 4px solid #5B9BD5;
}
div[data-testid="stMetric"]:nth-of-type(2) { border-left-color: #70AD47; }
div[data-testid="stMetric"]:nth-of-type(3) { border-left-color: #FFC000; }
div[data-testid="stMetric"]:nth-of-type(4) { border-left-color: #ED7D31; }
div[data-testid="stMetric"]:nth-of-type(5) { border-left-color: #A855F7; }
div[data-testid="stMetric"] label {
    font-size: 0.72rem !important; font-weight: 600 !important;
    letter-spacing: 0.3px; opacity: 0.65; text-transform: uppercase;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-size: 1.4rem !important; font-weight: 700 !important;
}
@media (prefers-color-scheme: light) {
    div[data-testid="stMetric"] { background: #FFFFFF; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
}
@media (prefers-color-scheme: dark) {
    div[data-testid="stMetric"] { background: rgba(255,255,255,0.04); }
}
button[data-baseweb="tab"] { font-weight: 700 !important; font-size: 1rem !important; padding: 12px 24px !important; }
div[data-baseweb="tab-highlight"] { background-color: #5B9BD5 !important; height: 3px !important; }
.main h2 { font-size: 1.1rem !important; font-weight: 700 !important; margin-top: 0.2rem !important; margin-bottom: 0.3rem !important; }
hr { margin: 0.8rem 0 !important; opacity: 0.3; }
div[data-testid="stSegmentedControl"] { max-width: 420px !important; }
div[data-testid="stSegmentedControl"] button {
    font-size: 0.7rem !important; padding: 2px 10px !important;
    min-height: 0 !important; height: 26px !important;
}
div[data-testid="stDateInput"] { max-width: 130px !important; }
div[data-testid="stDateInput"] input {
    font-size: 0.8rem !important; padding: 5px 8px !important;
    border: 1.5px solid #94a3b8 !important; border-radius: 5px !important;
    background: #fff !important; color: #1e293b !important;
}
div[data-testid="stDateInput"] input:hover { border-color: #5B9BD5 !important; }
div[data-testid="stDateInput"] label {
    font-size: 0.65rem !important; margin-bottom: 1px !important; opacity: 0.7;
}
@media (prefers-color-scheme: dark) {
    div[data-testid="stDateInput"] input {
        background: #1e293b !important; border-color: #475569 !important; color: #e2e8f0 !important;
    }
}
.main [data-testid="stColumn"]:has(div[data-testid="stDateInput"]) {
    flex: 0 0 auto !important; width: auto !important; min-width: 0 !important;
}
.main .stDownloadButton > button {
    font-size: 0.7rem !important; padding: 3px 10px !important; height: 28px !important;
}
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
    'indigo': '#7B8FD4', 'revenue': '#5B9BD5', 'cost': '#E05252', 
    'margin': '#70AD47', 'margin_rate': '#FFC000',
    'game': '#5B9BD5', 'gathering': '#A855F7', 'iaa': '#70AD47', 
    'offerwall': '#ED7D31', 'pc_highlight': '#E05252',
}
PUB_COLORS = ['#5B9BD5', '#ED7D31', '#70AD47', '#A855F7', '#E05252', '#4DB8A4', '#FFC000', '#A0AEC0']

ALLOWED_DOMAIN = "fsn.co.kr"

if not st.user.is_logged_in:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("")
        st.markdown("### 📊 E프로젝트 대시보드")
        st.caption(f"@{ALLOWED_DOMAIN} 계정으로 로그인해 주세요")
        st.markdown("")
        if st.button("🔑 Google 계정으로 로그인", use_container_width=True):
            st.login()
    st.stop()

user_email = st.user.get("email", "")
if not user_email.endswith(f"@{ALLOWED_DOMAIN}"):
    st.error(f"⛔ @{ALLOWED_DOMAIN} 계정만 접근할 수 있습니다. ({user_email})")
    if st.button("다른 계정으로 로그인"):
        st.logout()
    st.stop()

def init_session_state():
    defaults = {
        'pc_kpi_di_from': None, 'pc_kpi_di_to': None, 'pc_kpi_seg': None,
        'pc_tr_di_from': None, 'pc_tr_di_to': None, 'pc_tr_seg': None,
        'cp_kpi_di_from': None, 'cp_kpi_di_to': None, 'cp_kpi_seg': None,
        'cp_tr_di_from': None, 'cp_tr_di_to': None, 'cp_tr_seg': None,
        'data_loaded': {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

def safe_execution(default_return=None, error_message="오류가 발생했습니다"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                st.error(f"{error_message}: {str(e)}")
                if default_return is not None:
                    return default_return
                return pd.DataFrame() if 'load' in func.__name__ else None
        return wrapper
    return decorator

@st.cache_data(ttl=600, show_spinner=False)
def load_sheet_data(sheet_name: str) -> pd.DataFrame:
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(st.secrets["spreadsheet_id"])
        ws = sh.worksheet(sheet_name)
        data = ws.get_all_records()
        
        if not data:
            st.warning(f"시트 '{sheet_name}'에 데이터가 없습니다.")
            return pd.DataFrame()
        
        return pd.DataFrame(data)
    
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ 시트 '{sheet_name}'을 찾을 수 없습니다.")
        return pd.DataFrame()
    except gspread.exceptions.APIError as e:
        st.error(f"❌ Google Sheets API 오류: {e}")
        return pd.DataFrame()
    except KeyError as e:
        st.error(f"❌ 설정 오류: {e}. Secrets 설정을 확인하세요.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ 데이터 로드 중 예상치 못한 오류: {e}")
        return pd.DataFrame()

def safe_divide(numerator, denominator, default=0, scale=100):
    if denominator == 0 or pd.isna(denominator) or pd.isna(numerator):
        return default
    result = (numerator / denominator) * scale
    if not np.isfinite(result):
        return default
    return round(result, 2)

@safe_execution(default_return=pd.DataFrame(), error_message="포인트클릭 데이터 처리 중 오류")
def load_pointclick(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    
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
    
    if df['date'].isna().all():
        st.error("⚠️ 유효한 날짜 데이터가 없습니다.")
        return pd.DataFrame()
    
    numeric_cols = ['unit_price','clicks','conversions','ad_revenue','media_cost','media_rate','margin','margin_rate','cvr']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    df = df[df['date'].notna()].copy()
    return df

@safe_execution(default_return=pd.DataFrame(), error_message="캐시플레이 데이터 처리 중 오류")
def load_cashplay(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    
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
    
    if df['date'].isna().all():
        st.error("⚠️ 유효한 날짜 데이터가 없습니다.")
        return pd.DataFrame()
    
    for c in [x for x in df.columns if x != 'date']:
        df[c] = df[c].replace('-', 0)
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    df = df[df['date'].notna()].copy()
    df['revenue_total'] = df['game_total'] + df['gathering_pointclick'] + df['iaa_total'] + df['offerwall_total']
    df['cost_total'] = df['reward_total']
    df['margin'] = df['revenue_total'] - df['cost_total']
    df['margin_rate'] = df.apply(lambda row: safe_divide(row['margin'], row['revenue_total'], default=0, scale=100), axis=1)
    df['pointclick_revenue'] = df['gathering_pointclick'] + df['offerwall_pointclick']
    df['pointclick_ratio'] = df.apply(lambda row: safe_divide(row['pointclick_revenue'], row['revenue_total'], default=0, scale=100), axis=1)
    
    return df

def format_won(n):
    if pd.isna(n):
        return "₩0"
    if abs(n) >= 1e8:
        return f"₩{n/1e8:.1f}억"
    if abs(n) >= 1e4:
        return f"₩{n/1e4:,.0f}만"
    return f"₩{n:,.0f}"

def format_number(n):
    if pd.isna(n):
        return "0"
    return f"{n:,.0f}"

def format_pct(n):
    if pd.isna(n) or not np.isfinite(n):
        return "0.0%"
    return f"{n:,.1f}%"

def get_comparison_metrics(df, start_date, end_date):
    if df.empty or 'date' not in df.columns:
        empty_series = pd.Series(dtype=float)
        return empty_series, empty_series, lambda x: 0.0, lambda x, y, z: 0.0
    
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        empty_series = pd.Series(dtype=float)
        return empty_series, empty_series, lambda x: 0.0, lambda x, y, z: 0.0

    curr_mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
    curr_df = df[curr_mask]

    duration = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration - 1)

    prev_mask = (df['date'].dt.date >= prev_start) & (df['date'].dt.date <= prev_end)
    prev_df = df[prev_mask]

    curr_sums = curr_df[numeric_cols].sum() if not curr_df.empty else pd.Series(0, index=numeric_cols)
    prev_sums = prev_df[numeric_cols].sum() if not prev_df.empty else pd.Series(0, index=numeric_cols)

    def get_delta(col):
        c = curr_sums.get(col, 0)
        p = prev_sums.get(col, 0)
        return safe_divide(c - p, p, default=0, scale=100)

    def get_rate_delta(numerator_col, denominator_col, scale=100):
        cn = curr_sums.get(numerator_col, 0)
        cd = curr_sums.get(denominator_col, 0)
        pn = prev_sums.get(numerator_col, 0)
        pd_val = prev_sums.get(denominator_col, 0)
        
        curr_rate = safe_divide(cn, cd, default=0, scale=scale)
        prev_rate = safe_divide(pn, pd_val, default=0, scale=scale)
        
        return round(curr_rate - prev_rate, 1)

    return curr_sums, prev_sums, get_delta, get_rate_delta

def make_weekly(df, date_col='date', group_col=None):
    if df.empty or date_col not in df.columns:
        return pd.DataFrame()
    
    t = df.copy()
    try:
        t['week_start'] = t[date_col].dt.to_period('W').apply(lambda x: x.start_time)
    except Exception as e:
        st.warning(f"주 단위 변환 중 오류: {e}")
        return pd.DataFrame()
    
    nums = [c for c in t.columns if pd.api.types.is_numeric_dtype(t[c]) and c != date_col]
    if not nums:
        return pd.DataFrame()
    
    if group_col and group_col in t.columns:
        r = t.groupby(['week_start', group_col], dropna=False)[nums].sum().reset_index()
    else:
        r = t.groupby('week_start', dropna=False)[nums].sum().reset_index()
    
    if r.empty:
        return pd.DataFrame()
    
    return r.rename(columns={'week_start': 'week'})

def week_label(d):
    try:
        e = d + timedelta(days=6)
        return f"{d.month}/{d.day}~{e.month}/{e.day}"
    except:
        return str(d)

def fmt_axis_won(val):
    if pd.isna(val):
        return "0"
    av = abs(val)
    sign = "-" if val < 0 else ""
    if av >= 1e8:
        return f"{sign}{val/1e8:.1f}억"
    if av >= 1e4:
        return f"{sign}{val/1e4:,.0f}만"
    return f"{sign}{val:,.0f}"

def set_y_korean_ticks(fig, values):
    if not values or len(values) == 0:
        return
    
    values = [v for v in values if pd.notna(v) and np.isfinite(v)]
    if not values:
        return
    
    vmax = max(abs(v) for v in values)
    if vmax == 0:
        return
    
    nice = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
    unit = 1e8 if vmax >= 1e8 else (1e4 if vmax >= 1e4 else 1)
    step_units = (vmax / 5) / unit
    chosen = 1
    for n in nice:
        if n >= step_units:
            chosen = n
            break
    step = chosen * unit
    mn = min(values)
    tick_vals, tick_texts = [], []
    v = 0
    while v <= vmax * 1.15:
        tick_vals.append(v)
        tick_texts.append(fmt_axis_won(v))
        if mn < 0:
            tick_vals.append(-v)
            tick_texts.append(fmt_axis_won(-v))
        v += step
        if v > 1e12:
            break
    
    try:
        fig.update_yaxes(tickvals=tick_vals, ticktext=tick_texts, selector=dict(overlaying=None))
    except:
        pass

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(size=11),
    margin=dict(t=15, b=45, l=55, r=15),
    legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
    xaxis=dict(showgrid=False, tickfont=dict(size=10)),
    yaxis=dict(gridcolor="rgba(128,128,128,0.12)", gridwidth=1, tickfont=dict(size=10)),
    hoverlabel=dict(font_size=11),
    hovermode="x unified",
)

def apply_layout(fig, extra=None):
    layout = {**CHART_LAYOUT}
    if extra:
        layout.update(extra)
    fig.update_layout(**layout)
    return fig

def quick_date_picker(data_min, data_max, prefix, default_mode="이번달"):
    today = date.today()
    yesterday = today - timedelta(days=1)

    presets = {
        "오늘": (today, today),
        "어제": (yesterday, yesterday),
        "이번주": (today - timedelta(days=today.weekday()), today),
        "전주": (today - timedelta(days=today.weekday() + 7), today - timedelta(days=today.weekday() + 1)),
        "이번달": (today.replace(day=1), today),
        "전월": ((today.replace(day=1) - timedelta(days=1)).replace(day=1), today.replace(day=1) - timedelta(days=1)),
        "올해": (date(today.year, 1, 1), today),
    }

    def clamp(d):
        try:
            return max(data_min, min(d, data_max))
        except:
            return d

    key_from = f"{prefix}_di_from"
    key_to = f"{prefix}_di_to"
    key_seg = f"{prefix}_seg"

    if st.session_state[key_from] is None:
        ds, de = presets.get(default_mode, (today, today))
        st.session_state[key_from] = clamp(ds)
        st.session_state[key_to] = clamp(de)
    else:
        st.session_state[key_from] = clamp(st.session_state[key_from])
        st.session_state[key_to] = clamp(st.session_state[key_to])

    current_from = st.session_state[key_from]
    current_to = st.session_state[key_to]
    current_preset = None
    for label, (ps, pe) in presets.items():
        if clamp(ps) == current_from and clamp(pe) == current_to:
            current_preset = label
            break

    selected = st.segmented_control(
        label="기간 선택",
        options=list(presets.keys()),
        default=current_preset,
        key=key_seg,
        label_visibility="collapsed",
    )

    if selected and selected in presets:
        ps, pe = presets[selected]
        new_from = clamp(ps)
        new_to = clamp(pe)
        if new_from != current_from or new_to != current_to:
            st.session_state[key_from] = new_from
            st.session_state[key_to] = new_to

    dc1, dc2, _ = st.columns([1, 1, 8], gap="small")
    with dc1:
        d_from = st.date_input("시작일", min_value=data_min, max_value=data_max, key=key_from)
    with dc2:
        d_to = st.date_input("종료일", min_value=data_min, max_value=data_max, key=key_to)

    return d_from, d_to

def render_pointclick_dashboard(df: pd.DataFrame):
    if df.empty:
        st.warning("포인트클릭 데이터가 없습니다.")
        return

    try:
        dmin, dmax = df['date'].min().date(), df['date'].max().date()
    except:
        st.error("날짜 데이터를 처리할 수 없습니다.")
        return

    with st.sidebar:
        st.markdown("### 🔍 포인트클릭 필터")
        pub_types = ['전체'] + sorted(df['publisher_type'].dropna().unique().tolist())
        sel_pub = st.selectbox("퍼블리셔 타입", pub_types, key="pc_pub")
        ad_types = ['전체'] + sorted(df['ad_type'].dropna().unique().tolist())
        sel_ad = st.selectbox("광고 타입", ad_types, key="pc_adtype")
        os_types = ['전체'] + sorted(df['os'].dropna().unique().tolist())
        sel_os = st.selectbox("OS", os_types, key="pc_os")

    f = df.copy()
    if sel_pub != '전체': f = f[f['publisher_type'] == sel_pub]
    if sel_ad != '전체': f = f[f['ad_type'] == sel_ad]
    if sel_os != '전체': f = f[f['os'] == sel_os]

    @st.fragment
    def pc_kpi_section():
        st.markdown("## 📈 핵심 지표")
        kf, kt = quick_date_picker(dmin, dmax, "pc_kpi", "이번달")
        kdf = f[(f['date'].dt.date >= kf) & (f['date'].dt.date <= kt)]
        curr_sums, prev_sums, get_delta, get_rate_delta = get_comparison_metrics(f, kf, kt)

        if kdf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
        else:
            tr = curr_sums.get('ad_revenue', 0)
            tm = curr_sums.get('margin', 0)
            tc = curr_sums.get('clicks', 0)
            tv = curr_sums.get('conversions', 0)
            amr = safe_divide(tm, tr, default=0, scale=100)
            acvr = safe_divide(tv, tc, default=0, scale=100)

            m1,m2,m3,m4,m5 = st.columns(5)
            m1.metric("광고비(매출)", format_won(tr), delta=f"{get_delta('ad_revenue'):+.1f}%")
            m2.metric("마진", format_won(tm), delta=f"{get_delta('margin'):+.1f}%")
            m3.metric("마진율", format_pct(amr), delta=f"{get_rate_delta('margin', 'ad_revenue'):+.1f}%p")
            m4.metric("전환수", format_number(tv), delta=f"{get_delta('conversions'):+.1f}%")
            m5.metric("평균 CVR", format_pct(acvr), delta=f"{get_rate_delta('conversions', 'clicks'):+.1f}%p")

        st.markdown("---")
        st.markdown("## 🔎 상세 분석")
        st.caption(f"📅 {kf} ~ {kt}")

        if kdf.empty:
            return

        tab_conv, tab_adv, tab_media, tab_raw = st.tabs(["🎯 광고타입별 전환", "📊 광고주별", "📡 매체별", "📋 Raw"])

        with tab_conv:
            at = kdf.groupby('ad_type', dropna=False).agg(
                clicks=('clicks','sum'), conversions=('conversions','sum'),
                ad_revenue=('ad_revenue','sum'), margin=('margin','sum')
            ).reset_index()
            at['cvr'] = at.apply(lambda row: safe_divide(row['conversions'], row['clicks'], default=0, scale=100), axis=1)
            at['margin_rate'] = at.apply(lambda row: safe_divide(row['margin'], row['ad_revenue'], default=0, scale=100), axis=1)
            at = at.sort_values('ad_revenue', ascending=False)

            cc1, cc2 = st.columns(2)
            with cc1:
                fig_a = go.Figure()
                fig_a.add_trace(go.Bar(x=at['ad_type'], y=at['clicks'], name='클릭수',
                    marker_color=PASTEL['blue'], opacity=0.55, hovertemplate="클릭: %{y:,.0f}<extra></extra>"))
                fig_a.add_trace(go.Bar(x=at['ad_type'], y=at['conversions'], name='전환수',
                    marker_color=PASTEL['green'], opacity=0.85, hovertemplate="전환: %{y:,.0f}<extra></extra>"))
                fig_a.add_trace(go.Scatter(x=at['ad_type'], y=at['cvr'], name='CVR', mode='lines+markers+text',
                    text=[f"{v:.1f}%" for v in at['cvr']], textposition='top center', textfont=dict(size=9, color=PASTEL['red']),
                    line=dict(color=PASTEL['red'], width=2.5), marker=dict(size=8),
                    yaxis='y2', hovertemplate="CVR: %{y:.2f}%<extra></extra>"))
                max_cvr = at['cvr'].max() if not at.empty else 10
                apply_layout(fig_a, dict(barmode='group', height=380,
                    yaxis2=dict(title="", overlaying='y', side='right', range=[0, max(max_cvr*1.5, 10)], 
                        ticksuffix="%", gridcolor="rgba(0,0,0,0)", tickfont=dict(color=PASTEL['red']))))
                st.plotly_chart(fig_a, use_container_width=True)
            with cc2:
                d = at.copy()
                for c in ['clicks','conversions','ad_revenue','margin']:
                    d[c] = d[c].apply(lambda x: f"{x:,.0f}")
                d['cvr'] = d['cvr'].apply(lambda x: f"{x:.2f}%")
                d['margin_rate'] = d['margin_rate'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(d.rename(columns={'ad_type':'광고타입','clicks':'클릭수','conversions':'전환수',
                    'ad_revenue':'광고비(매출)','margin':'마진','cvr':'CVR','margin_rate':'마진율'}), 
                    use_container_width=True, hide_index=True, height=380)

            st.markdown("##### 일별 광고타입별 전환수")
            dat = kdf.groupby(['date','ad_type'], dropna=False).agg(conversions=('conversions','sum')).reset_index()
            fig_d = go.Figure()
            for a in sorted(kdf['ad_type'].dropna().unique()):
                s = dat[dat['ad_type']==a].sort_values('date')
                fig_d.add_trace(go.Scatter(x=s['date'], y=s['conversions'], name=a, mode='lines+markers',
                    hovertemplate=f"<b>{a}</b><br>%{{x|%m/%d}}: %{{y:,.0f}}건<extra></extra>"))
            apply_layout(fig_d, dict(height=300))
            st.plotly_chart(fig_d, use_container_width=True)

        with tab_adv:
            adv = kdf.groupby('advertiser', dropna=False).agg(
                ad_revenue=('ad_revenue','sum'), margin=('margin','sum'),
                conversions=('conversions','sum'), clicks=('clicks','sum'), ad_count=('ad_name','nunique')
            ).reset_index()
            adv['margin_rate'] = adv.apply(lambda row: safe_divide(row['margin'], row['ad_revenue'], default=0, scale=100), axis=1)
            adv['cvr'] = adv.apply(lambda row: safe_divide(row['conversions'], row['clicks'], default=0, scale=100), axis=1)
            adv = adv.sort_values('ad_revenue', ascending=False)

            a1, a2 = st.columns(2)
            with a1:
                fig_av = px.bar(adv.head(15), x='ad_revenue', y='advertiser', orientation='h',
                    color='margin_rate', color_continuous_scale='RdYlGn',
                    labels={'ad_revenue':'광고비(매출)','advertiser':'광고주','margin_rate':'마진율(%)'})
                fig_av.update_traces(hovertemplate="<b>%{y}</b><br>매출: %{x:,.0f}원<extra></extra>")
                apply_layout(fig_av, dict(height=420, yaxis=dict(autorange="reversed")))
                st.plotly_chart(fig_av, use_container_width=True)
            with a2:
                da = adv.copy()
                for c in ['ad_revenue','margin','conversions','clicks','ad_count']:
                    da[c] = da[c].apply(lambda x: f"{x:,.0f}")
                da['margin_rate'] = da['margin_rate'].apply(lambda x: f"{x:.1f}%")
                da['cvr'] = da['cvr'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(da.rename(columns={'advertiser':'광고주','ad_revenue':'광고비(매출)','margin':'마진',
                    'margin_rate':'마진율','conversions':'전환수','clicks':'클릭수','cvr':'CVR','ad_count':'광고수'}),
                    use_container_width=True, hide_index=True, height=420)

        with tab_media:
            med = kdf.groupby('media_name', dropna=False).agg(
                ad_revenue=('ad_revenue','sum'), margin=('margin','sum'),
                conversions=('conversions','sum'), clicks=('clicks','sum')
            ).reset_index()
            med['margin_rate'] = med.apply(lambda row: safe_divide(row['margin'], row['ad_revenue'], default=0, scale=100), axis=1)
            med['cvr'] = med.apply(lambda row: safe_divide(row['conversions'], row['clicks'], default=0, scale=100), axis=1)
            med = med.sort_values('ad_revenue', ascending=False)

            mc1, mc2 = st.columns(2)
            with mc1:
                fig_m = px.treemap(med.head(20), path=['media_name'], values='ad_revenue',
                    color='margin_rate', color_continuous_scale='RdYlGn')
                fig_m.update_traces(hovertemplate="<b>%{label}</b><br>매출: %{value:,.0f}원<extra></extra>")
                fig_m.update_layout(height=420, margin=dict(t=10,b=10), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_m, use_container_width=True)
            with mc2:
                dm = med.copy()
                for c in ['ad_revenue','margin','conversions','clicks']:
                    dm[c] = dm[c].apply(lambda x: f"{x:,.0f}")
                dm['margin_rate'] = dm['margin_rate'].apply(lambda x: f"{x:.1f}%")
                dm['cvr'] = dm['cvr'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(dm.rename(columns={'media_name':'매체명','ad_revenue':'광고비(매출)','margin':'마진',
                    'margin_rate':'마진율','conversions':'전환수','clicks':'클릭수','cvr':'CVR'}),
                    use_container_width=True, hide_index=True, height=420)

        with tab_raw:
            raw = kdf.copy().sort_values('date', ascending=False)
            rd = raw.copy()
            rd['date'] = rd['date'].dt.strftime('%Y-%m-%d')
            rd = rd[['date','publisher_type','ad_name','media_name','advertiser','os','ad_type','unit_price','clicks','conversions','cvr','ad_revenue','media_cost','margin','margin_rate']]
            for c in ['unit_price','clicks','conversions','ad_revenue','media_cost','margin']:
                rd[c] = rd[c].apply(lambda x: f"{x:,.0f}")
            rd['cvr'] = rd['cvr'].apply(lambda x: f"{x:.2f}%")
            rd['margin_rate'] = rd['margin_rate'].apply(lambda x: f"{x:.1f}%")
            st.dataframe(rd.rename(columns={'date':'일자','publisher_type':'퍼블리셔','ad_name':'광고명',
                'media_name':'매체명','advertiser':'광고주','os':'OS','ad_type':'광고타입','unit_price':'단가',
                'clicks':'클릭수','conversions':'전환수','cvr':'CVR','ad_revenue':'광고비','media_cost':'매체비',
                'margin':'마진','margin_rate':'마진율'}), use_container_width=True, hide_index=True, height=500)
            csv = raw.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 CSV 다운로드", csv, file_name=f"포인트클릭_{kf}_{kt}.csv", mime="text/csv")

    @st.fragment
    def pc_trend_section():
        st.markdown("## 💰 매출 · 마진 추이 (주단위, 월요일 기준)")
        tf, tt = quick_date_picker(dmin, dmax, "pc_tr", "올해")
        tdf = f[(f['date'].dt.date >= tf) & (f['date'].dt.date <= tt)]

        if tdf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
        else:
            wp = make_weekly(tdf, group_col='publisher_type')
            if not wp.empty:
                wp['wl'] = wp['week'].apply(week_label)
            
            wt = make_weekly(tdf)
            if not wt.empty:
                wt['margin_rate'] = wt.apply(lambda row: safe_divide(row['margin'], row['ad_revenue'], default=0, scale=100), axis=1)
                wt['wl'] = wt['week'].apply(week_label)
            
            if wp.empty or wt.empty:
                st.info("주간 데이터를 생성할 수 없습니다.")
                return
            
            pubs = sorted(wp['publisher_type'].dropna().unique().tolist())

            cl, cr = st.columns(2)

            with cl:
                st.markdown("#### 광고비(매출)")
                fig = go.Figure()
                for i, p in enumerate(pubs):
                    s = wp[wp['publisher_type']==p].sort_values('week')
                    fig.add_trace(go.Bar(x=s['wl'], y=s['ad_revenue'], name=p, marker_color=PUB_COLORS[i%len(PUB_COLORS)],
                        hovertemplate=f"<b>{p}</b><br>%{{y:,.0f}}원<extra></extra>"))
                apply_layout(fig, dict(barmode='stack', height=380, xaxis_tickangle=-45))
                set_y_korean_ticks(fig, wp['ad_revenue'].tolist())
                st.plotly_chart(fig, use_container_width=True)

            with cr:
                st.markdown("#### 마진 · 마진율")
                fig2 = go.Figure()
                for i, p in enumerate(pubs):
                    s = wp[wp['publisher_type']==p].sort_values('week')
                    fig2.add_trace(go.Bar(x=s['wl'], y=s['margin'], name=p, marker_color=PUB_COLORS[i%len(PUB_COLORS)],
                        showlegend=False, hovertemplate=f"<b>{p}</b><br>%{{y:,.0f}}원<extra></extra>"))
                
                max_margin_rate = wt['margin_rate'].max() if not wt.empty else 10
                fig2.add_trace(go.Scatter(x=wt['wl'], y=wt['margin_rate'], name='마진율', mode='lines+markers+text',
                    text=[f"{v:.1f}%" for v in wt['margin_rate']], textposition='top center', 
                    textfont=dict(size=9, color=PASTEL['yellow']), line=dict(color=PASTEL['yellow'], width=2.5),
                    marker=dict(size=6, color=PASTEL['yellow']), yaxis='y2', hovertemplate="마진율: %{y:.1f}%<extra></extra>"))
                apply_layout(fig2, dict(barmode='stack', height=380, xaxis_tickangle=-45,
                    yaxis2=dict(title="", overlaying='y', side='right', range=[0, max(max_margin_rate*1.5, 10)],
                        ticksuffix="%", gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10, color=PASTEL['yellow']))))
                set_y_korean_ticks(fig2, wp['margin'].tolist())
                st.plotly_chart(fig2, use_container_width=True)

    pc_kpi_section()
    pc_trend_section()

def render_cashplay_dashboard(df: pd.DataFrame):
    if df.empty:
        st.warning("캐시플레이 데이터가 없습니다.")
        return

    try:
        dmin, dmax = df['date'].min().date(), df['date'].max().date()
    except:
        st.error("날짜 데이터를 처리할 수 없습니다.")
        return

    @st.fragment
    def cp_kpi_section():
        st.markdown("## 📈 핵심 지표")
        kf, kt = quick_date_picker(dmin, dmax, "cp_kpi", "이번달")
        kdf = df[(df['date'].dt.date >= kf) & (df['date'].dt.date <= kt)]
        curr_sums, prev_sums, get_delta, get_rate_delta = get_comparison_metrics(df, kf, kt)

        if kdf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
        else:
            tr = curr_sums.get('revenue_total', 0)
            tc = curr_sums.get('cost_total', 0)
            tm = curr_sums.get('margin', 0)
            amr = safe_divide(tm, tr, default=0, scale=100)
            tpc = curr_sums.get('pointclick_revenue', 0)
            apcr = safe_divide(tpc, tr, default=0, scale=100)

            m1,m2,m3,m4,m5 = st.columns(5)
            m1.metric("총 매출", format_won(tr), delta=f"{get_delta('revenue_total'):+.1f}%")
            m2.metric("매입(리워드)", format_won(tc), delta=f"{get_delta('cost_total'):+.1f}%")
            m3.metric("마진", format_won(tm), delta=f"{get_delta('margin'):+.1f}%")
            m4.metric("마진율", format_pct(amr), delta=f"{get_rate_delta('margin', 'revenue_total'):+.1f}%p")
            m5.metric("🌟 자사 비중", format_pct(apcr), delta=f"{get_rate_delta('pointclick_revenue', 'revenue_total'):+.1f}%p")

        st.markdown("---")
        st.markdown("## 📊 매출 구성 분석")
        st.caption(f"📅 {kf} ~ {kt}")

        if not kdf.empty:
            col1, col2 = st.columns(2)
            with col1:
                cats = {'게임': kdf['game_total'].sum(), '게더링': kdf['gathering_pointclick'].sum(),
                    'IAA': kdf['iaa_total'].sum(), '오퍼월': kdf['offerwall_total'].sum()}
                cdf_pie = pd.DataFrame({'category': cats.keys(), 'amount': cats.values()})
                fig_p = px.pie(cdf_pie, values='amount', names='category',
                    color_discrete_sequence=[PASTEL['game'], PASTEL['gathering'], PASTEL['iaa'], PASTEL['offerwall']], hole=0.5)
                fig_p.update_traces(textinfo='label+percent', textfont_size=11,
                    hovertemplate="<b>%{label}</b><br>%{value:,.0f}원 (%{percent})<extra></extra>")
                fig_p.update_layout(height=360, margin=dict(t=25,b=10), showlegend=False,
                    title_text="카테고리별 매출", title_font=dict(size=12), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_p, use_container_width=True)

            with col2:
                ks2 = kdf.sort_values('date')
                fig_s = go.Figure()
                for nm, col, clr in [('게임','game_total',PASTEL['game']),('게더링','gathering_pointclick',PASTEL['gathering']),
                                      ('IAA','iaa_total',PASTEL['iaa']),('오퍼월','offerwall_total',PASTEL['offerwall'])]:
                    fig_s.add_trace(go.Bar(x=ks2['date'], y=ks2[col], name=nm, marker_color=clr,
                        hovertemplate=f"<b>{nm}</b><br>%{{x|%m/%d}}: %{{y:,.0f}}원<extra></extra>"))
                apply_layout(fig_s, dict(barmode='stack', height=360, title_text="일별 매출 구성", title_font=dict(size=12)))
                set_y_korean_ticks(fig_s, ks2['revenue_total'].tolist())
                st.plotly_chart(fig_s, use_container_width=True)

        st.markdown("---")
        st.markdown("## 🌟 자사 서비스(포인트클릭) 기여도")

        if not kdf.empty:
            pcr = kdf['pointclick_revenue'].sum()
            ext = kdf['revenue_total'].sum() - pcr
            c3, c4 = st.columns(2)

            with c3:
                fig_b = go.Figure()
                fig_b.add_trace(go.Bar(x=['자사(포인트클릭)'], y=[pcr], marker_color=PASTEL['pc_highlight'],
                    text=[format_won(pcr)], textposition='auto', width=0.35, hovertemplate="자사: %{y:,.0f}원<extra></extra>"))
                fig_b.add_trace(go.Bar(x=['외부 매체'], y=[ext], marker_color=PASTEL['gray'],
                    text=[format_won(ext)], textposition='auto', width=0.35, hovertemplate="외부: %{y:,.0f}원<extra></extra>"))
                apply_layout(fig_b, dict(height=330, showlegend=False))
                set_y_korean_ticks(fig_b, [pcr, ext])
                st.plotly_chart(fig_b, use_container_width=True)

            with c4:
                ks3 = kdf.sort_values('date')
                fig_dd = go.Figure()
                fig_dd.add_trace(go.Bar(x=ks3['date'], y=ks3['gathering_pointclick'], name='게더링(PC)',
                    marker_color=PASTEL['red'], hovertemplate="게더링: %{y:,.0f}원<extra></extra>"))
                fig_dd.add_trace(go.Bar(x=ks3['date'], y=ks3['offerwall_pointclick'], name='오퍼월(PC)',
                    marker_color=PASTEL['pink'], hovertemplate="오퍼월: %{y:,.0f}원<extra></extra>"))
                apply_layout(fig_dd, dict(barmode='stack', height=330))
                st.plotly_chart(fig_dd, use_container_width=True)

            total_all = kdf['revenue_total'].sum()
            pc_r = safe_divide(pcr, total_all, default=0, scale=100)
            st.info(f"**자사 매출** – 게더링: **{format_won(kdf['gathering_pointclick'].sum())}** · "
                f"오퍼월: **{format_won(kdf['offerwall_pointclick'].sum())}** · "
                f"합계: **{format_won(pcr)}** (전체의 **{format_pct(pc_r)}**)")

        st.markdown("---")
        st.markdown("## 🔎 매출 상세")

        if not kdf.empty:
            dt1, dt2, dt3, dt4, dt5, dt6 = st.tabs(["🎮 게임", "🔗 게더링", "📺 IAA", "📱 오퍼월", "💸 리워드", "📋 전체"])

            with dt1:
                cols_g = ['date','game_direct','game_dsp','game_rs','game_acquisition','game_total']
                dg = kdf[cols_g].copy().sort_values('date', ascending=False)
                dg['date'] = dg['date'].dt.strftime('%Y-%m-%d')
                for c in cols_g[1:]: dg[c] = dg[c].apply(lambda x: f"{x:,.0f}")
                st.dataframe(dg.rename(columns={'date':'날짜','game_direct':'직거래','game_dsp':'DSP','game_rs':'RS','game_acquisition':'인수','game_total':'합계'}),
                    use_container_width=True, hide_index=True)
                gs = kdf.sort_values('date')
                fig_g = go.Figure()
                for nm, col in [('직거래','game_direct'),('DSP','game_dsp'),('RS','game_rs'),('인수','game_acquisition')]:
                    fig_g.add_trace(go.Bar(x=gs['date'], y=gs[col], name=nm, hovertemplate=f"{nm}: %{{y:,.0f}}원<extra></extra>"))
                apply_layout(fig_g, dict(barmode='stack', height=330))
                st.plotly_chart(fig_g, use_container_width=True)

            with dt2:
                dgt = kdf[['date','gathering_pointclick']].copy().sort_values('date', ascending=False)
                dgt['date'] = dgt['date'].dt.strftime('%Y-%m-%d')
                dgt['gathering_pointclick'] = dgt['gathering_pointclick'].apply(lambda x: f"{x:,.0f}")
                st.dataframe(dgt.rename(columns={'date':'날짜','gathering_pointclick':'포인트클릭'}), use_container_width=True, hide_index=True)

            with dt3:
                cols_i = ['date','iaa_levelplay','iaa_adwhale','iaa_hubble','iaa_total']
                di = kdf[cols_i].copy().sort_values('date', ascending=False)
                di['date'] = di['date'].dt.strftime('%Y-%m-%d')
                for c in cols_i[1:]: di[c] = di[c].apply(lambda x: f"{x:,.0f}")
                st.dataframe(di.rename(columns={'date':'날짜','iaa_levelplay':'레벨플레이','iaa_adwhale':'애드웨일','iaa_hubble':'허블','iaa_total':'합계'}),
                    use_container_width=True, hide_index=True)
                ias = kdf.sort_values('date')
                fig_i = go.Figure()
                for nm, col in [('레벨플레이','iaa_levelplay'),('애드웨일','iaa_adwhale'),('허블','iaa_hubble')]:
                    fig_i.add_trace(go.Bar(x=ias['date'], y=ias[col], name=nm, hovertemplate=f"{nm}: %{{y:,.0f}}원<extra></extra>"))
                apply_layout(fig_i, dict(barmode='stack', height=330))
                st.plotly_chart(fig_i, use_container_width=True)

            with dt4:
                cols_o = ['date','offerwall_adpopcorn','offerwall_pointclick','offerwall_ive',
                          'offerwall_adforus','offerwall_addison','offerwall_adjo','offerwall_total']
                do = kdf[cols_o].copy().sort_values('date', ascending=False)
                do['date'] = do['date'].dt.strftime('%Y-%m-%d')
                for c in cols_o[1:]: do[c] = do[c].apply(lambda x: f"{x:,.0f}")
                st.dataframe(do.rename(columns={'date':'날짜','offerwall_adpopcorn':'애드팝콘','offerwall_pointclick':'⭐포인트클릭',
                    'offerwall_ive':'아이브','offerwall_adforus':'애드포러스','offerwall_addison':'애디슨','offerwall_adjo':'애드조','offerwall_total':'합계'}),
                    use_container_width=True, hide_index=True)
                ows = kdf.sort_values('date')
                fig_o = go.Figure()
                traces = [('⭐포인트클릭','offerwall_pointclick',PASTEL['pc_highlight']),('애드팝콘','offerwall_adpopcorn',None),
                          ('아이브','offerwall_ive',None),('애드포러스','offerwall_adforus',None),('애디슨','offerwall_addison',None),('애드조','offerwall_adjo',None)]
                for nm, col, clr in traces:
                    kw = dict(marker_color=clr) if clr else {}
                    fig_o.add_trace(go.Bar(x=ows['date'], y=ows[col], name=nm, hovertemplate=f"{nm}: %{{y:,.0f}}원<extra></extra>", **kw))
                apply_layout(fig_o, dict(barmode='stack', height=330))
                st.plotly_chart(fig_o, use_container_width=True)

            with dt5:
                rw1, rw2 = st.columns(2)
                with rw1:
                    rws = kdf.sort_values('date')
                    fig_rw = go.Figure()
                    fig_rw.add_trace(go.Bar(x=rws['date'], y=rws['reward_paid'], name='유상',
                        marker_color=PASTEL['red'], hovertemplate="유상: %{y:,.0f}원<extra></extra>"))
                    fig_rw.add_trace(go.Bar(x=rws['date'], y=rws['reward_free'], name='무상',
                        marker_color=PASTEL['orange'], hovertemplate="무상: %{y:,.0f}원<extra></extra>"))
                    apply_layout(fig_rw, dict(barmode='stack', height=330))
                    st.plotly_chart(fig_rw, use_container_width=True)
                with rw2:
                    fig_rp = px.pie(values=[kdf['reward_paid'].sum(), kdf['reward_free'].sum()], names=['유상','무상'],
                        color_discrete_sequence=[PASTEL['red'], PASTEL['orange']], hole=0.5)
                    fig_rp.update_traces(textinfo='label+percent+value', hovertemplate="<b>%{label}</b><br>%{value:,.0f}원 (%{percent})<extra></extra>")
                    fig_rp.update_layout(height=330, margin=dict(t=25,b=10), title_text="유상/무상 비율", 
                        title_font=dict(size=12), paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_rp, use_container_width=True)

            with dt6:
                full = kdf.copy().sort_values('date', ascending=False)
                fd = full.copy()
                fd['date'] = fd['date'].dt.strftime('%Y-%m-%d')
                for c in [col for col in fd.columns if col != 'date']:
                    if pd.api.types.is_numeric_dtype(full[c]):
                        if 'rate' in c or 'ratio' in c:
                            fd[c] = fd[c].apply(lambda x: f"{x:.1f}%")
                        else:
                            fd[c] = fd[c].apply(lambda x: f"{x:,.0f}")
                st.dataframe(fd, use_container_width=True, hide_index=True, height=500)
                csv = full.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 CSV 다운로드", csv, file_name=f"캐시플레이_{kf}_{kt}.csv", mime="text/csv")

    @st.fragment
    def cp_trend_section():
        st.markdown("## 💰 매출 · 비용 · 마진 추이 (주단위, 월요일 기준)")
        tf, tt = quick_date_picker(dmin, dmax, "cp_tr", "올해")
        tdf = df[(df['date'].dt.date >= tf) & (df['date'].dt.date <= tt)]

        if not tdf.empty:
            w = make_weekly(tdf)
            if not w.empty:
                w['margin_rate'] = w.apply(lambda row: safe_divide(row['margin'], row['revenue_total'], default=0, scale=100), axis=1)
                w['wl'] = w['week'].apply(week_label)

                fig = go.Figure()
                fig.add_trace(go.Bar(x=w['wl'], y=w['revenue_total'], name='총 매출',
                    marker_color=PASTEL['blue'], opacity=0.75, hovertemplate="매출: %{y:,.0f}원<extra></extra>"))
                fig.add_trace(go.Bar(x=w['wl'], y=-w['cost_total'], name='매입(리워드)',
                                     marker_color=PASTEL['red'], opacity=0.75, customdata=w['cost_total'],
                    hovertemplate="매입: %{customdata:,.0f}원<extra></extra>"))
                fig.add_trace(go.Scatter(x=w['wl'], y=w['margin'], name='마진', mode='lines+markers+text',
                    text=[format_won(v) for v in w['margin']], textposition='top center',
                    textfont=dict(size=9, color=PASTEL['green']),
                    line=dict(color=PASTEL['green'], width=2.5), marker=dict(size=7, color=PASTEL['green']),
                    hovertemplate="마진: %{y:,.0f}원<extra></extra>"))
                apply_layout(fig, dict(barmode='relative', height=400, xaxis_tickangle=-45))
                all_vals = list(w['revenue_total']) + list(-w['cost_total']) + list(w['margin'])
                set_y_korean_ticks(fig, all_vals)
                st.plotly_chart(fig, use_container_width=True)

    cp_kpi_section()
    cp_trend_section()

def main():
    st.title("📊 E프로젝트 대시보드")
    st.caption(f"마지막 새로고침: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    with st.sidebar:
        user_name = st.user.get("name", "")
        user_email = st.user.get("email", "")
        if user_name:
            st.markdown(f"👤 **{user_name}**")
            st.caption(user_email)
        if st.button("🚪 로그아웃", use_container_width=True):
            st.logout()
        st.markdown("---")
        st.markdown("## ⚙️ 설정")
        if st.button("🔄 데이터 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.session_state['data_loaded'] = {}
            st.rerun()
        st.markdown("---")

    tab_pc, tab_cp = st.tabs(["🟢 PointClick (B2B)", "🔵 CashPlay (B2C)"])

    with tab_pc:
        if 'pointclick' not in st.session_state['data_loaded']:
            with st.spinner("포인트클릭 데이터 로딩 중..."):
                pc_raw = load_sheet_data(SHEET_NAMES["포인트클릭"]["db"])
                pc_df = load_pointclick(pc_raw)
                st.session_state['data_loaded']['pointclick'] = pc_df
        else:
            pc_df = st.session_state['data_loaded']['pointclick']
        
        render_pointclick_dashboard(pc_df)

    with tab_cp:
        if 'cashplay' not in st.session_state['data_loaded']:
            with st.spinner("캐시플레이 데이터 로딩 중..."):
                cp_raw = load_sheet_data(SHEET_NAMES["캐시플레이"]["db"])
                cp_df = load_cashplay(cp_raw)
                st.session_state['data_loaded']['cashplay'] = cp_df
        else:
            cp_df = st.session_state['data_loaded']['cashplay']
        
        render_cashplay_dashboard(cp_df)

if __name__ == "__main__":
    main()