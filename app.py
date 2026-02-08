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
# CSS — Power BI 스타일 + 버튼 소형화 커스텀
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

/* ── 버튼 스타일 (작고 오밀조밀하게) ── */
div.stButton > button {
    width: 100%;
    border-radius: 4px;
    font-size: 11px !important;  /* 폰트 축소 */
    padding: 2px 5px !important; /* 패딩 축소 */
    height: auto !important;
    min-height: 28px !important; /* 높이 축소 */
    line-height: 1.2 !important;
    background-color: #f7f9fc;
    border: 1px solid #e2e8f0;
    color: #4a5568;
}
div.stButton > button:hover {
    border-color: #5B9BD5;
    color: #5B9BD5;
    background-color: #ebf8ff;
}
div.stButton > button:active, div.stButton > button:focus {
    border-color: #5B9BD5;
    background-color: #5B9BD5;
    color: white;
}

/* ── 날짜 입력창 스타일 ── */
div[data-testid="stDateInput"] {
    margin-top: -10px; /* 버튼과의 간격 좁히기 */
}
div[data-testid="stDateInput"] label {
    display: none; /* 라벨 숨김 (깔끔하게) */
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
# 데이터 로딩
# ============================================================
@st.cache_data(ttl=600)
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
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception:
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
    df['pointclick_ratio'] = (df['pointclick_revenue'] / df['revenue_total'] * 100).round(1).replace([float('inf'), float('-inf')], 0)
    return df

# ============================================================
# 유틸리티 & 차트
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

def fmt_axis_won(val):
    av = abs(val)
    sign = "-" if val < 0 else ""
    if av >= 1e8: return f"{sign}{val/1e8:.1f}억"
    if av >= 1e4: return f"{sign}{val/1e4:,.0f}만"
    return f"{sign}{val:,.0f}"

def set_y_korean_ticks(fig, values):
    if len(values) == 0: return
    vmax = max(abs(v) for v in values if v == v)
    if vmax == 0: return
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
        if v > 1e12: break
    fig.update_yaxes(tickvals=tick_vals, ticktext=tick_texts, selector=dict(overlaying=None))

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
    l = {**CHART_LAYOUT}
    if extra: l.update(extra)
    fig.update_layout(**l)
    return fig

# ============================================================
# [중요] 기간별 비교 로직 (Day-over-Day 대신 Period-over-Period)
# ============================================================
def get_comparison_metrics(df, start_date, end_date):
    if df.empty: return {}, lambda x: 0
    
    # 1. 현재 기간
    curr_mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
    curr_df = df[curr_mask]
    
    # 2. 직전 기간 (동일 일수만큼 뒤로 이동)
    duration = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration - 1)
    
    prev_mask = (df['date'].dt.date >= prev_start) & (df['date'].dt.date <= prev_end)
    prev_df = df[prev_mask]
    
    # 3. 집계
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    curr_sums = curr_df[numeric_cols].sum()
    prev_sums = prev_df[numeric_cols].sum()
    
    def get_delta(col):
        c = curr_sums.get(col, 0)
        p = prev_sums.get(col, 0)
        if p == 0: return 0
        return ((c - p) / p) * 100

    return curr_sums, get_delta

# ============================================================
# [UI 수정] 빠른 날짜 선택기 (버튼 1열, 날짜입력 2열)
# ============================================================
def quick_date_picker(data_min, data_max, prefix, default_mode="이번 달"):
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    presets = {
        "오늘": (today, today),
        "어제": (yesterday, yesterday),
        "이번주": (today - timedelta(days=today.weekday()), today),
        "전주": (today - timedelta(days=today.weekday() + 7), today - timedelta(days=today.weekday() + 1)),
        "이번달": (today.replace(day=1), today),
        "전월": ((today.replace(day=1) - timedelta(days=1)).replace(day=1), today.replace(day=1) - timedelta(days=1)),
    }

    if f"{prefix}_from" not in st.session_state:
        ds, de = presets.get(default_mode, (today, today))
        st.session_state[f"{prefix}_from"] = max(ds, data_min)
        st.session_state[f"{prefix}_to"] = min(de, data_max)

    # 1. 버튼 행 (작고 오밀조밀하게)
    # 비율: 버튼 6개(1) + 나머지 여백(6) -> 버튼들이 왼쪽으로 쏠리게 됨
    btn_cols = st.columns([1, 1, 1, 1, 1, 1, 6], gap="small")
    
    clicked_preset = None
    for i, (label, (ps, pe)) in enumerate(presets.items()):
        with btn_cols[i]:
            if st.button(label, key=f"{prefix}_btn_{label}"):
                clicked_preset = (ps, pe)

    if clicked_preset:
        st.session_state[f"{prefix}_from"] = max(clicked_preset[0], data_min)
        st.session_state[f"{prefix}_to"] = min(clicked_preset[1], data_max)
        st.rerun()

    # 2. 날짜 입력 행 (버튼 바로 아래)
    dc1, dc2, _ = st.columns([1.2, 1.2, 5])
    with dc1:
        d_from = st.date_input("", value=st.session_state[f"{prefix}_from"],
                               min_value=data_min, max_value=data_max, key=f"{prefix}_di_from")
    with dc2:
        d_to = st.date_input("", value=st.session_state[f"{prefix}_to"],
                             min_value=data_min, max_value=data_max, key=f"{prefix}_di_to")
    
    st.session_state[f"{prefix}_from"] = d_from
    st.session_state[f"{prefix}_to"] = d_to

    return d_from, d_to


# ============================================================
# 포인트클릭 대시보드
# ============================================================
def render_pointclick_dashboard(df: pd.DataFrame):
    if df.empty:
        st.warning("포인트클릭 데이터가 없습니다.")
        return

    dmin, dmax = df['date'].min().date(), df['date'].max().date()

    with st.sidebar:
        st.markdown("### 🔍 포인트클릭 필터")
        pub_types = ['전체'] + sorted(df['publisher_type'].unique().tolist())
        sel_pub = st.selectbox("퍼블리셔 타입", pub_types, key="pc_pub")
        
    f = df.copy()
    if sel_pub != '전체': f = f[f['publisher_type'] == sel_pub]

    # ── 핵심 지표 ──
    st.markdown("### 📈 핵심 지표")
    kf, kt = quick_date_picker(dmin, dmax, "pc_kpi", "이번달")
    
    # 전일비 로직 적용
    curr_sums, get_delta = get_comparison_metrics(f, kf, kt)

    if curr_sums.empty:
        st.info("선택한 기간에 데이터가 없습니다.")
    else:
        tr = curr_sums['ad_revenue']
        tm = curr_sums['margin']
        tc = curr_sums['clicks']
        tv = curr_sums['conversions']
        amr = (tm / tr * 100) if tr else 0
        acvr = (tv / tc * 100) if tc else 0

        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("광고비(매출)", format_won(tr), delta=f"{get_delta('ad_revenue'):+.1f}%")
        m2.metric("마진", format_won(tm), delta=f"{get_delta('margin'):+.1f}%")
        m3.metric("마진율", format_pct(amr))
        m4.metric("전환수", format_number(tv), delta=f"{get_delta('conversions'):+.1f}%")
        m5.metric("평균 CVR", format_pct(acvr))

    st.markdown("---")

    # ── 매출/마진 추이 ──
    st.markdown("### 💰 매출 · 마진 추이")
    tf, tt = quick_date_picker(dmin, dmax, "pc_tr", "전월")
    tdf = f[(f['date'].dt.date >= tf) & (f['date'].dt.date <= tt)]

    if tdf.empty:
        st.info("선택한 기간에 데이터가 없습니다.")
    else:
        wp = make_weekly(tdf, group_col='publisher_type')
        wp['wl'] = wp['week'].apply(week_label)
        wt = make_weekly(tdf)
        wt['margin_rate'] = (wt['margin'] / wt['ad_revenue'] * 100).round(1).replace([float('inf'),float('-inf')],0).fillna(0)
        wt['wl'] = wt['week'].apply(week_label)
        pubs = sorted(wp['publisher_type'].unique().tolist())

        cl, cr = st.columns(2)
        with cl:
            st.markdown("#### 광고비(매출)")
            fig = go.Figure()
            for i, p in enumerate(pubs):
                s = wp[wp['publisher_type']==p].sort_values('week')
                fig.add_trace(go.Bar(
                    x=s['wl'], y=s['ad_revenue'], name=p,
                    marker_color=PUB_COLORS[i%len(PUB_COLORS)],
                    hovertemplate=f"<b>{p}</b><br>%{{y:,.0f}}원<extra></extra>"
                ))
            apply_layout(fig, dict(barmode='stack', height=380, xaxis_tickangle=-45))
            set_y_korean_ticks(fig, wp['ad_revenue'].tolist())
            st.plotly_chart(fig, use_container_width=True)

        with cr:
            st.markdown("#### 마진 · 마진율")
            fig2 = go.Figure()
            for i, p in enumerate(pubs):
                s = wp[wp['publisher_type']==p].sort_values('week')
                fig2.add_trace(go.Bar(
                    x=s['wl'], y=s['margin'], name=p,
                    marker_color=PUB_COLORS[i%len(PUB_COLORS)], showlegend=False,
                    hovertemplate=f"<b>{p}</b><br>%{{y:,.0f}}원<extra></extra>"
                ))
            fig2.add_trace(go.Scatter(
                x=wt['wl'], y=wt['margin_rate'], name='마진율',
                mode='lines+markers+text',
                text=[f"{v:.1f}%" for v in wt['margin_rate']],
                textposition='top center', textfont=dict(size=9, color=PASTEL['yellow']),
                line=dict(color=PASTEL['yellow'], width=2.5),
                marker=dict(size=6, color=PASTEL['yellow']),
                yaxis='y2', hovertemplate="마진율: %{y:.1f}%<extra></extra>"
            ))
            apply_layout(fig2, dict(
                barmode='stack', height=380, xaxis_tickangle=-45,
                yaxis2=dict(title="", overlaying='y', side='right',
                    range=[0, max(wt['margin_rate'].max()*1.5, 10)],
                    ticksuffix="%", gridcolor="rgba(0,0,0,0)",
                    tickfont=dict(size=10, color=PASTEL['yellow']))
            ))
            set_y_korean_ticks(fig2, wp['margin'].tolist())
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ── 상세 분석 ──
    st.markdown("### 🔎 상세 분석")
    st.caption(f"📅 조회 기간: {kf} ~ {kt}")
    
    kdf = f[(f['date'].dt.date >= kf) & (f['date'].dt.date <= kt)]
    if kdf.empty: return

    t1, t2, t3, t4 = st.tabs(["🎯 전환 성과", "📊 광고주별", "📡 매체별", "📋 Raw 데이터"])

    with t1:
        at = kdf.groupby('ad_type').agg(clicks=('clicks','sum'), conversions=('conversions','sum'), ad_revenue=('ad_revenue','sum')).reset_index()
        at['cvr'] = (at['conversions']/at['clicks']*100).fillna(0)
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=at['ad_type'], y=at['conversions'], name="전환수", marker_color=PASTEL['green']))
            fig.add_trace(go.Scatter(x=at['ad_type'], y=at['cvr'], name="CVR", yaxis="y2", line=dict(color=PASTEL['red'])))
            apply_layout(fig, dict(yaxis2=dict(overlaying='y', side='right', showgrid=False), title="광고타입별 전환/CVR"))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.dataframe(at, use_container_width=True, hide_index=True)

    with t2:
        adv = kdf.groupby('advertiser').agg(ad_revenue=('ad_revenue','sum'), margin=('margin','sum')).reset_index().sort_values('ad_revenue', ascending=False).head(20)
        st.dataframe(adv, use_container_width=True, hide_index=True)

    with t3:
        med = kdf.groupby('media_name').agg(ad_revenue=('ad_revenue','sum'), margin=('margin','sum')).reset_index().sort_values('ad_revenue', ascending=False).head(20)
        st.dataframe(med, use_container_width=True, hide_index=True)

    with t4:
        st.dataframe(kdf.sort_values('date', ascending=False), use_container_width=True, hide_index=True)


# ============================================================
# 캐시플레이 대시보드
# ============================================================
def render_cashplay_dashboard(df: pd.DataFrame):
    if df.empty:
        st.warning("캐시플레이 데이터가 없습니다.")
        return

    dmin, dmax = df['date'].min().date(), df['date'].max().date()

    st.markdown("### 📈 핵심 지표")
    kf, kt = quick_date_picker(dmin, dmax, "cp_kpi", "이번달")
    
    curr_sums, get_delta = get_comparison_metrics(df, kf, kt)

    if curr_sums.empty:
        st.info("데이터가 없습니다.")
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

    st.markdown("### 💰 매출 · 비용 · 마진 추이")
    tf, tt = quick_date_picker(dmin, dmax, "cp_tr", "전월")
    tdf = df[(df['date'].dt.date >= tf) & (df['date'].dt.date <= tt)]

    if not tdf.empty:
        w = make_weekly(tdf)
        w['margin_rate'] = (w['margin']/w['revenue_total']*100).fillna(0)
        w['wl'] = w['week'].apply(week_label)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=w['wl'], y=w['revenue_total'], name="매출", marker_color=PASTEL['blue']))
        fig.add_trace(go.Bar(x=w['wl'], y=-w['cost_total'], name="매입", marker_color=PASTEL['red']))
        fig.add_trace(go.Scatter(x=w['wl'], y=w['margin'], name="마진", line=dict(color=PASTEL['green'])))
        apply_layout(fig, dict(barmode='relative', height=400))
        set_y_korean_ticks(fig, list(w['revenue_total']) + list(w['margin']))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    
    kdf = df[(df['date'].dt.date >= kf) & (df['date'].dt.date <= kt)]
    if kdf.empty: return

    st.markdown("### 📊 상세 데이터")
    st.dataframe(kdf.sort_values('date', ascending=False), use_container_width=True, hide_index=True)


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
        # 실제 데이터 로딩 주석 해제하여 사용
        pc_raw = load_sheet_data(SHEET_NAMES["포인트클릭"]["db"])
        pc_df = load_pointclick(pc_raw)
        render_pointclick_dashboard(pc_df)

    with tab_cp:
        cp_raw = load_sheet_data(SHEET_NAMES["캐시플레이"]["db"])
        cp_df = load_cashplay(cp_raw)
        render_cashplay_dashboard(cp_df)

if __name__ == "__main__":
    main()