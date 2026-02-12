"""포인트클릭 GA4 대시보드"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import (
    safe_divide, format_number, format_pct,
    apply_layout, quick_date_picker
)
from config.constants import PASTEL


def render_pointclick_ga_dashboard(df: pd.DataFrame):
    """포인트클릭 GA4 대시보드 렌더링"""
    if df.empty:
        st.warning("포인트클릭 GA4 데이터가 없습니다.")
        return

    try:
        df['date'] = pd.to_datetime(df['date'])
        dmin, dmax = df['date'].min().date(), df['date'].max().date()
    except:
        st.error("날짜 데이터를 처리할 수 없습니다.")
        return

    @st.fragment
    def traffic_section():
        st.markdown("## 📊 트래픽 지표")
        tf, tt = quick_date_picker(dmin, dmax, "pc_ga_traffic", "이번달")
        tdf = df[(df['date'].dt.date >= tf) & (df['date'].dt.date <= tt)]

        if tdf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
            return

        # 일별 집계
        daily = tdf.groupby('date').agg({
            'activeUsers': 'sum',
            'active7DayUsers': 'sum',
            'active28DayUsers': 'sum',
            'newUsers': 'sum',
            'sessions': 'sum',
            'screenPageViews': 'sum'
        }).reset_index()

        # 전체 합계
        total_dau = daily['activeUsers'].sum()
        total_wau = daily['active7DayUsers'].max()  # WAU는 최대값 사용
        total_mau = daily['active28DayUsers'].max()  # MAU는 최대값 사용
        total_new = daily['newUsers'].sum()
        total_sessions = daily['sessions'].sum()
        total_views = daily['screenPageViews'].sum()

        # 지표 카드
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("DAU (총합)", format_number(total_dau))
        m2.metric("WAU (최대)", format_number(total_wau))
        m3.metric("MAU (최대)", format_number(total_mau))
        m4.metric("신규 사용자", format_number(total_new))
        m5.metric("세션 수", format_number(total_sessions))
        m6.metric("페이지뷰", format_number(total_views))

        st.markdown("---")

        # DAU/WAU/MAU 트렌드 차트
        st.markdown("#### 일별 활성 사용자 추이")
        fig_users = go.Figure()
        fig_users.add_trace(go.Scatter(
            x=daily['date'], y=daily['activeUsers'], name='DAU',
            mode='lines+markers', line=dict(color=PASTEL['blue'], width=2),
            marker=dict(size=6), hovertemplate="DAU: %{y:,.0f}<extra></extra>"
        ))
        fig_users.add_trace(go.Scatter(
            x=daily['date'], y=daily['active7DayUsers'], name='WAU',
            mode='lines', line=dict(color=PASTEL['green'], width=2, dash='dash'),
            hovertemplate="WAU: %{y:,.0f}<extra></extra>"
        ))
        fig_users.add_trace(go.Scatter(
            x=daily['date'], y=daily['active28DayUsers'], name='MAU',
            mode='lines', line=dict(color=PASTEL['purple'], width=2, dash='dot'),
            hovertemplate="MAU: %{y:,.0f}<extra></extra>"
        ))
        apply_layout(fig_users, dict(height=350, hovermode='x unified'))
        st.plotly_chart(fig_users, use_container_width=True)

        # 세션 & 페이지뷰 차트
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 일별 세션 수")
            fig_sessions = go.Figure()
            fig_sessions.add_trace(go.Bar(
                x=daily['date'], y=daily['sessions'],
                marker_color=PASTEL['orange'], opacity=0.7,
                hovertemplate="세션: %{y:,.0f}<extra></extra>"
            ))
            apply_layout(fig_sessions, dict(height=300, showlegend=False))
            st.plotly_chart(fig_sessions, use_container_width=True)

        with col2:
            st.markdown("#### 일별 페이지뷰")
            fig_views = go.Figure()
            fig_views.add_trace(go.Bar(
                x=daily['date'], y=daily['screenPageViews'],
                marker_color=PASTEL['cyan'], opacity=0.7,
                hovertemplate="페이지뷰: %{y:,.0f}<extra></extra>"
            ))
            apply_layout(fig_views, dict(height=300, showlegend=False))
            st.plotly_chart(fig_views, use_container_width=True)

    @st.fragment
    def event_section():
        st.markdown("## 🎯 이벤트 분석")
        ef, et = quick_date_picker(dmin, dmax, "pc_ga_event", "이번달")
        edf = df[(df['date'].dt.date >= ef) & (df['date'].dt.date <= et)]

        if edf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
            return

        st.caption(f"📅 {ef} ~ {et}")

        # 메뉴별 집계 (pageTitle 기준)
        menu_stats = edf.groupby('pageTitle', dropna=False).agg({
            'sessions': 'sum',                      # 진입수
            'activeUsers': 'sum',                   # 참여수
            'averageSessionDuration': 'mean',       # 평균 세션 시간
            'engagementRate': 'mean'                # 참여율
        }).reset_index()

        # (not set) 제거
        menu_stats = menu_stats[~menu_stats['pageTitle'].astype(str).str.contains('not set', case=False, na=False)]

        # 정렬
        menu_stats = menu_stats.sort_values('sessions', ascending=False)

        # 컬럼명 변경
        menu_stats.columns = ['메뉴명', '진입수', '참여수', '평균 세션타임(초)', '참여율(%)']

        st.markdown("### 📑 메뉴별 세션타임, 진입수, 참여수, 참여율")

        if menu_stats.empty:
            st.info("메뉴별 데이터가 없습니다.")
            return

        # Top 15로 제한
        top_menus = menu_stats.head(15)

        # 차트 2개 (세션타임 & 진입수, 참여수 & 참여율)
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 메뉴별 평균 세션타임 & 진입수")
            fig1 = go.Figure()
            fig1.add_trace(go.Bar(
                x=top_menus['메뉴명'], y=top_menus['진입수'],
                name='진입수', marker_color=PASTEL['blue'], opacity=0.6,
                yaxis='y', hovertemplate="진입수: %{y:,.0f}<extra></extra>"
            ))
            fig1.add_trace(go.Scatter(
                x=top_menus['메뉴명'], y=top_menus['평균 세션타임(초)'],
                name='평균 세션타임', mode='lines+markers+text',
                text=[f"{v:.0f}초" for v in top_menus['평균 세션타임(초)']],
                textposition='top center', textfont=dict(size=9, color=PASTEL['red']),
                line=dict(color=PASTEL['red'], width=2.5), marker=dict(size=8),
                yaxis='y2', hovertemplate="세션타임: %{y:.1f}초<extra></extra>"
            ))
            max_time = top_menus['평균 세션타임(초)'].max() if not top_menus.empty else 100
            apply_layout(fig1, dict(
                height=400, xaxis_tickangle=-45,
                yaxis2=dict(title="", overlaying='y', side='right',
                    range=[0, max(max_time*1.3, 100)],
                    ticksuffix="초", gridcolor="rgba(0,0,0,0)",
                    tickfont=dict(color=PASTEL['red']))
            ))
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            st.markdown("#### 메뉴별 참여수 & 참여율")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=top_menus['메뉴명'], y=top_menus['참여수'],
                name='참여수', marker_color=PASTEL['green'], opacity=0.6,
                yaxis='y', hovertemplate="참여수: %{y:,.0f}<extra></extra>"
            ))
            fig2.add_trace(go.Scatter(
                x=top_menus['메뉴명'], y=top_menus['참여율(%)'],
                name='참여율', mode='lines+markers+text',
                text=[f"{v:.1f}%" for v in top_menus['참여율(%)']],
                textposition='top center', textfont=dict(size=9, color=PASTEL['purple']),
                line=dict(color=PASTEL['purple'], width=2.5), marker=dict(size=8),
                yaxis='y2', hovertemplate="참여율: %{y:.1f}%<extra></extra>"
            ))
            max_rate = top_menus['참여율(%)'].max() if not top_menus.empty else 100
            apply_layout(fig2, dict(
                height=400, xaxis_tickangle=-45,
                yaxis2=dict(title="", overlaying='y', side='right',
                    range=[0, max(max_rate*1.3, 100)],
                    ticksuffix="%", gridcolor="rgba(0,0,0,0)",
                    tickfont=dict(color=PASTEL['purple']))
            ))
            st.plotly_chart(fig2, use_container_width=True)

        # 테이블
        st.markdown("#### 전체 메뉴 통계")
        display_df = menu_stats.copy()
        display_df['평균 세션타임(초)'] = display_df['평균 세션타임(초)'].apply(lambda x: f"{x:.1f}")
        display_df['참여율(%)'] = display_df['참여율(%)'].apply(lambda x: f"{x:.1f}")
        display_df['진입수'] = display_df['진입수'].apply(lambda x: f"{x:,.0f}")
        display_df['참여수'] = display_df['참여수'].apply(lambda x: f"{x:,.0f}")

        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

        # CSV 다운로드
        csv = menu_stats.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📥 CSV 다운로드", csv,
            file_name=f"포인트클릭_GA_메뉴분석_{ef}_{et}.csv",
            mime="text/csv"
        )

    traffic_section()
    st.markdown("---")
    event_section()
