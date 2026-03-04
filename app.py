"""E프로젝트 대시보드 - 메인 앱"""
import streamlit as st
import pandas as pd
from datetime import datetime
from config.constants import SUPABASE_TABLES, CSS_STYLE, ALLOWED_DOMAIN
from utils.data_loader import load_supabase_data, load_pointclick, load_cashplay, load_ga4, load_media_master
from dashboards import (
    render_pointclick_dashboard, render_cashplay_dashboard,
    render_pointclick_ga_dashboard, render_cashplay_ga_dashboard,
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
        if st.button("🔑 Google 계정으로 로그인", width='stretch'):
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
        if st.button("🚪 로그아웃", width='stretch'):
            st.logout()
        st.markdown("---")
        st.markdown("## ⚙️ 설정")
        if st.button("🔄 데이터 새로고침", width='stretch'):
            st.cache_data.clear()
            st.session_state['data_loaded'] = {}
            st.session_state['data_extended'] = {}
            # 날짜 선택기 상태도 초기화 (데이터 범위 변경 시 반영)
            date_keys = [k for k in st.session_state if k.endswith(('_di_from', '_di_to', '_seg'))]
            for k in date_keys:
                del st.session_state[k]
            st.rerun()
        st.markdown("---")

    # ── 단계별 데이터 로딩 (탭 렌더 전에 순서대로 처리) ──────────────────
    # 1단계: 포클 7일
    if 'pointclick' not in st.session_state['data_loaded']:
        with st.spinner("포인트클릭 데이터 로딩 중..."):
            pc_df = load_pointclick(load_supabase_data(
                SUPABASE_TABLES["포인트클릭"]["db"], recent_days=7
            ))
            st.session_state['data_loaded']['pointclick'] = pc_df

    # 2단계: 캐플 7일
    if 'cashplay' not in st.session_state['data_loaded']:
        with st.spinner("캐시플레이 데이터 로딩 중..."):
            cp_df = load_cashplay(load_supabase_data(
                SUPABASE_TABLES["캐시플레이"]["db"], recent_days=7
            ))
            st.session_state['data_loaded']['cashplay'] = cp_df

    # 3단계: 포클 45일 (조용히 업데이트)
    if 'pointclick_45' not in st.session_state['data_extended']:
        pc_df = load_pointclick(load_supabase_data(
            SUPABASE_TABLES["포인트클릭"]["db"], recent_days=45
        ))
        st.session_state['data_loaded']['pointclick'] = pc_df
        st.session_state['data_extended']['pointclick_45'] = True

    # 4단계: 캐플 45일 (조용히 업데이트)
    if 'cashplay_45' not in st.session_state['data_extended']:
        cp_df = load_cashplay(load_supabase_data(
            SUPABASE_TABLES["캐시플레이"]["db"], recent_days=45
        ))
        st.session_state['data_loaded']['cashplay'] = cp_df
        st.session_state['data_extended']['cashplay_45'] = True

    # 5단계: 포클 90일 (조용히 업데이트, 전체 로드 대신 90일 상한으로 속도 개선)
    if 'pointclick_90' not in st.session_state['data_extended']:
        pc_df = load_pointclick(load_supabase_data(
            SUPABASE_TABLES["포인트클릭"]["db"], recent_days=90
        ))
        st.session_state['data_loaded']['pointclick'] = pc_df
        st.session_state['data_extended']['pointclick_90'] = True

    # 6단계: 캐플 90일 (조용히 업데이트)
    if 'cashplay_90' not in st.session_state['data_extended']:
        cp_df = load_cashplay(load_supabase_data(
            SUPABASE_TABLES["캐시플레이"]["db"], recent_days=90
        ))
        st.session_state['data_loaded']['cashplay'] = cp_df
        st.session_state['data_extended']['cashplay_90'] = True

    pc_df = st.session_state['data_loaded'].get('pointclick', pd.DataFrame())
    cp_df = st.session_state['data_loaded'].get('cashplay', pd.DataFrame())
    # ────────────────────────────────────────────────────────────────────────

    tab_pc, tab_cp, tab_pc_ga, tab_cp_ga = st.tabs([
        "🟢 PointClick (B2B)",
        "🔵 CashPlay (B2C)",
        "📊 PointClick GA",
        "📊 CashPlay GA",
    ])

    with tab_pc:
        render_pointclick_dashboard(pc_df)

    with tab_cp:
        render_cashplay_dashboard(cp_df)

    with tab_pc_ga:
        if 'pointclick_ga' not in st.session_state['data_loaded']:
            with st.spinner("포인트클릭 GA4 데이터 로딩 중..."):
                try:
                    pc_ga_raw = load_supabase_data(SUPABASE_TABLES["포인트클릭"]["ga"])
                    pc_ga_user_raw = load_supabase_data(SUPABASE_TABLES["포인트클릭"]["ga_user"])
                    st.session_state['data_loaded']['pointclick_ga'] = load_ga4(pc_ga_raw)
                    st.session_state['data_loaded']['pointclick_ga_user'] = load_ga4(pc_ga_user_raw)
                except Exception as e:
                    st.error(f"GA4 데이터 로드 실패: {str(e)}")
                    st.session_state['data_loaded']['pointclick_ga'] = None
                    st.session_state['data_loaded']['pointclick_ga_user'] = None

        pc_ga_df      = st.session_state['data_loaded'].get('pointclick_ga')
        pc_ga_user_df = st.session_state['data_loaded'].get('pointclick_ga_user')

        if pc_ga_df is not None:
            render_pointclick_ga_dashboard(pc_ga_df, pc_ga_user_df)
        else:
            st.warning("GA4 데이터를 불러올 수 없습니다.")

    with tab_cp_ga:
        if 'cashplay_ga' not in st.session_state['data_loaded']:
            with st.spinner("캐시플레이 GA4 데이터 로딩 중..."):
                try:
                    cp_ga_raw = load_supabase_data(SUPABASE_TABLES["캐시플레이"]["ga"])
                    cp_ga_user_raw = load_supabase_data(SUPABASE_TABLES["캐시플레이"]["ga_user"])
                    st.session_state['data_loaded']['cashplay_ga'] = load_ga4(cp_ga_raw)
                    st.session_state['data_loaded']['cashplay_ga_user'] = load_ga4(cp_ga_user_raw)
                except Exception as e:
                    st.error(f"GA4 데이터 로드 실패: {str(e)}")
                    st.session_state['data_loaded']['cashplay_ga'] = None
                    st.session_state['data_loaded']['cashplay_ga_user'] = None

        cp_ga_df      = st.session_state['data_loaded'].get('cashplay_ga')
        cp_ga_user_df = st.session_state['data_loaded'].get('cashplay_ga_user')

        if cp_ga_df is not None:
            render_cashplay_ga_dashboard(cp_ga_df, cp_ga_user_df)
        else:
            st.warning("GA4 데이터를 불러올 수 없습니다.")


main()
