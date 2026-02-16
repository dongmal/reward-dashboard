"""E프로젝트 대시보드 - 메인 앱"""
import streamlit as st
import pandas as pd
from datetime import datetime
from config.constants import SHEET_NAMES, CSS_STYLE, ALLOWED_DOMAIN
from utils.data_loader import load_sheet_data, load_pointclick, load_cashplay, load_ga4, load_media_master
from dashboards import (
    render_pointclick_dashboard, render_cashplay_dashboard,
    render_pointclick_ga_dashboard, render_cashplay_ga_dashboard,
    render_pointclick_ga_v2_dashboard, render_cashplay_ga_v2_dashboard
)


# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="E프로젝트 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일 적용
st.markdown(CSS_STYLE, unsafe_allow_html=True)


# ============================================================
# 인증 확인
# ============================================================
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


# ============================================================
# 세션 상태 초기화
# ============================================================
def init_session_state():
    defaults = {
        'pc_kpi_di_from': None,    'pc_kpi_di_to': None,    'pc_kpi_seg': None,
        'pc_detail_di_from': None, 'pc_detail_di_to': None, 'pc_detail_seg': None,
        'pc_tr_di_from': None,     'pc_tr_di_to': None,     'pc_tr_seg': None,
        'cp_kpi_di_from': None,    'cp_kpi_di_to': None,    'cp_kpi_seg': None,
        'cp_detail_di_from': None, 'cp_detail_di_to': None, 'cp_detail_seg': None,
        'cp_tr_di_from': None,     'cp_tr_di_to': None,     'cp_tr_seg': None,
        'pc_ga_traffic_di_from': None, 'pc_ga_traffic_di_to': None, 'pc_ga_traffic_seg': None,
        'pc_ga_event_di_from':   None, 'pc_ga_event_di_to':   None, 'pc_ga_event_seg':   None,
        'cp_ga_traffic_di_from': None, 'cp_ga_traffic_di_to': None, 'cp_ga_traffic_seg': None,
        'cp_ga_event_di_from':   None, 'cp_ga_event_di_to':   None, 'cp_ga_event_seg':   None,
        'pc_v2_media_di_from':   None, 'pc_v2_media_di_to':   None, 'pc_v2_media_seg':   None,
        'pc_v2_event_di_from':   None, 'pc_v2_event_di_to':   None, 'pc_v2_event_seg':   None,
        'pc_v2_page_di_from':    None, 'pc_v2_page_di_to':    None, 'pc_v2_page_seg':    None,
        'cp_v2_user_di_from':    None, 'cp_v2_user_di_to':    None, 'cp_v2_user_seg':    None,
        'cp_v2_button_di_from':  None, 'cp_v2_button_di_to':  None, 'cp_v2_button_seg':  None,
        'cp_v2_heatmap_di_from': None, 'cp_v2_heatmap_di_to': None, 'cp_v2_heatmap_seg': None,
        'data_loaded': {},
        'data_extended': {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()


# ============================================================
# 메인 함수
# ============================================================
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
            st.session_state['data_extended'] = {}
            st.rerun()
        st.markdown("---")

    # ── 단계별 데이터 로딩 (탭 렌더 전에 순서대로 처리) ──────────────────
    # 1단계: 포클 7일
    if 'pointclick' not in st.session_state['data_loaded']:
        with st.spinner("포인트클릭 데이터 로딩 중..."):
            pc_df = load_pointclick(load_sheet_data(SHEET_NAMES["포인트클릭"]["db"], recent_days=7))
            st.session_state['data_loaded']['pointclick'] = pc_df

    # 2단계: 캐플 7일
    if 'cashplay' not in st.session_state['data_loaded']:
        with st.spinner("캐시플레이 데이터 로딩 중..."):
            cp_df = load_cashplay(load_sheet_data(SHEET_NAMES["캐시플레이"]["db"], recent_days=7))
            st.session_state['data_loaded']['cashplay'] = cp_df

    # 3단계: 포클 45일 (조용히 업데이트)
    if 'pointclick_45' not in st.session_state['data_extended']:
        pc_df = load_pointclick(load_sheet_data(SHEET_NAMES["포인트클릭"]["db"], recent_days=45))
        st.session_state['data_loaded']['pointclick'] = pc_df
        st.session_state['data_extended']['pointclick_45'] = True

    # 4단계: 캐플 45일 (조용히 업데이트)
    if 'cashplay_45' not in st.session_state['data_extended']:
        cp_df = load_cashplay(load_sheet_data(SHEET_NAMES["캐시플레이"]["db"], recent_days=45))
        st.session_state['data_loaded']['cashplay'] = cp_df
        st.session_state['data_extended']['cashplay_45'] = True

    # 5단계: 포클 전체 (조용히 업데이트)
    if 'pointclick_full' not in st.session_state['data_extended']:
        pc_df = load_pointclick(load_sheet_data(SHEET_NAMES["포인트클릭"]["db"]))
        st.session_state['data_loaded']['pointclick'] = pc_df
        st.session_state['data_extended']['pointclick_full'] = True

    # 6단계: 캐플 전체 (조용히 업데이트)
    if 'cashplay_full' not in st.session_state['data_extended']:
        cp_df = load_cashplay(load_sheet_data(SHEET_NAMES["캐시플레이"]["db"]))
        st.session_state['data_loaded']['cashplay'] = cp_df
        st.session_state['data_extended']['cashplay_full'] = True

    pc_df = st.session_state['data_loaded'].get('pointclick', pd.DataFrame())
    cp_df = st.session_state['data_loaded'].get('cashplay', pd.DataFrame())
    # ────────────────────────────────────────────────────────────────────────

    tab_pc, tab_cp, tab_pc_ga, tab_cp_ga, tab_pc_ga_v2, tab_cp_ga_v2 = st.tabs([
        "🟢 PointClick (B2B)",
        "🔵 CashPlay (B2C)",
        "📊 PointClick GA",
        "📊 CashPlay GA",
        "🔍 PointClick GA 심화",
        "🔍 CashPlay GA 심화",
    ])

    with tab_pc:
        render_pointclick_dashboard(pc_df)

    with tab_cp:
        render_cashplay_dashboard(cp_df)

    with tab_pc_ga:
        if 'pointclick_ga' not in st.session_state['data_loaded']:
            with st.spinner("포인트클릭 GA4 데이터 로딩 중..."):
                try:
                    pc_ga_raw = load_sheet_data(SHEET_NAMES["포인트클릭"]["ga"])
                    pc_ga_df = load_ga4(pc_ga_raw)
                    st.session_state['data_loaded']['pointclick_ga'] = pc_ga_df
                except Exception as e:
                    st.error(f"GA4 데이터 로드 실패: {str(e)}")
                    st.session_state['data_loaded']['pointclick_ga'] = None
        else:
            pc_ga_df = st.session_state['data_loaded']['pointclick_ga']

        if pc_ga_df is not None:
            render_pointclick_ga_dashboard(pc_ga_df)
        else:
            st.warning("GA4 데이터를 불러올 수 없습니다.")

    with tab_cp_ga:
        if 'cashplay_ga' not in st.session_state['data_loaded']:
            with st.spinner("캐시플레이 GA4 데이터 로딩 중..."):
                try:
                    cp_ga_raw = load_sheet_data(SHEET_NAMES["캐시플레이"]["ga"])
                    cp_ga_df = load_ga4(cp_ga_raw)
                    st.session_state['data_loaded']['cashplay_ga'] = cp_ga_df
                except Exception as e:
                    st.error(f"GA4 데이터 로드 실패: {str(e)}")
                    st.session_state['data_loaded']['cashplay_ga'] = None
        else:
            cp_ga_df = st.session_state['data_loaded']['cashplay_ga']

        if cp_ga_df is not None:
            render_cashplay_ga_dashboard(cp_ga_df)
        else:
            st.warning("GA4 데이터를 불러올 수 없습니다.")

    with tab_pc_ga_v2:
        if 'pointclick_ga' not in st.session_state['data_loaded']:
            with st.spinner("포인트클릭 GA4 데이터 로딩 중..."):
                try:
                    pc_ga_raw = load_sheet_data(SHEET_NAMES["포인트클릭"]["ga"])
                    pc_ga_df = load_ga4(pc_ga_raw)
                    st.session_state['data_loaded']['pointclick_ga'] = pc_ga_df
                except Exception as e:
                    st.error(f"GA4 데이터 로드 실패: {str(e)}")
                    st.session_state['data_loaded']['pointclick_ga'] = None
        else:
            pc_ga_df = st.session_state['data_loaded']['pointclick_ga']

        if pc_ga_df is not None:
            render_pointclick_ga_v2_dashboard(pc_ga_df)
        else:
            st.warning("GA4 데이터를 불러올 수 없습니다.")

    with tab_cp_ga_v2:
        if 'cashplay_ga' not in st.session_state['data_loaded']:
            with st.spinner("캐시플레이 GA4 데이터 로딩 중..."):
                try:
                    cp_ga_raw = load_sheet_data(SHEET_NAMES["캐시플레이"]["ga"])
                    cp_ga_df = load_ga4(cp_ga_raw)
                    st.session_state['data_loaded']['cashplay_ga'] = cp_ga_df
                except Exception as e:
                    st.error(f"GA4 데이터 로드 실패: {str(e)}")
                    st.session_state['data_loaded']['cashplay_ga'] = None
        else:
            cp_ga_df = st.session_state['data_loaded']['cashplay_ga']

        if cp_ga_df is not None:
            render_cashplay_ga_v2_dashboard(cp_ga_df)
        else:
            st.warning("GA4 데이터를 불러올 수 없습니다.")


main()
