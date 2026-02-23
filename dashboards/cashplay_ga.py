"""캐시플레이 GA4 대시보드"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
from config.constants import PASTEL, CHART_LAYOUT


def render_cashplay_ga_dashboard(df: pd.DataFrame):
    if df.empty:
        st.warning("GA4 데이터가 없습니다.")
        return

    # ── 날짜 선택 (기준일 단일) ──────────────────────────────────────
    available_dates = sorted(df['date'].dropna().unique())
    yesterday = date.today() - timedelta(days=1)
    default_date = max(
        [d.date() for d in pd.to_datetime(available_dates) if d.date() <= yesterday],
        default=pd.to_datetime(available_dates[-1]).date() if available_dates else yesterday
    )

    col_date, _ = st.columns([1, 6])
    with col_date:
        target_date = st.date_input("기준일", value=default_date, key="cp_ga_date")

    target_ts = pd.Timestamp(target_date)

    # ── 기준일 데이터 ────────────────────────────────────────────────
    day_df = df[df['date'] == target_ts]

    # MAU: 최근 28일 activeUsers 일평균
    cutoff_28 = target_ts - timedelta(days=27)
    df_28 = df[(df['date'] >= cutoff_28) & (df['date'] <= target_ts)]
    daily_dau = df_28.groupby('date')['activeUsers'].sum()
    mau_avg = daily_dau.mean() if not daily_dau.empty else 0

    # DAU: 기준일 합계
    dau = day_df['activeUsers'].sum() if not day_df.empty else 0

    # 추가 지표
    sessions = day_df['sessions'].sum() if not day_df.empty else 0
    new_users = day_df['newUsers'].sum() if not day_df.empty else 0
    page_views = day_df['screenPageViews'].sum() if not day_df.empty else 0
    avg_duration = day_df['averageSessionDuration'].mean() if not day_df.empty else 0

    # ── KPI 메트릭 ───────────────────────────────────────────────────
    st.markdown(f"## 📊 CashPlay GA · 기준일: {target_date.strftime('%Y-%m-%d')}")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("DAU", f"{int(dau):,}")
    c2.metric("MAU (28일 일평균)", f"{mau_avg:,.1f}")
    c3.metric("세션", f"{int(sessions):,}")
    c4.metric("신규 사용자", f"{int(new_users):,}")
    c5.metric("평균 세션시간", f"{avg_duration:.0f}초")

    st.divider()

    # ── 섹션 1: DAU 추이 (최근 28일 라인 차트) ──────────────────────
    st.markdown("## DAU 추이 (최근 28일)")
    trend_df = df_28.groupby('date').agg(
        DAU=('activeUsers', 'sum'),
        세션=('sessions', 'sum'),
    ).reset_index().sort_values('date')

    if not trend_df.empty:
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=trend_df['date'], y=trend_df['DAU'],
            name='DAU', mode='lines+markers',
            line=dict(color=PASTEL['teal'], width=2),
            marker=dict(size=5),
            fill='tozeroy', fillcolor='rgba(77,184,164,0.12)'
        ))
        fig_trend.add_trace(go.Bar(
            x=trend_df['date'], y=trend_df['세션'],
            name='세션', yaxis='y2',
            marker_color='rgba(91,155,213,0.45)',
        ))
        fig_trend.add_vline(
            x=target_ts.timestamp() * 1000,
            line_dash='dash', line_color=PASTEL['orange'], line_width=1.5,
            annotation_text="기준일", annotation_position="top right"
        )
        layout = dict(**CHART_LAYOUT)
        layout['yaxis2'] = dict(
            overlaying='y', side='right',
            showgrid=False, tickfont=dict(size=10)
        )
        layout['height'] = 280
        fig_trend.update_layout(**layout)
        st.plotly_chart(fig_trend, width='stretch')

    st.divider()

    # ── 섹션 2: pageTitle 기준 진입률 ───────────────────────────────
    st.markdown("## 페이지별 진입률 (page_view vs click)")

    if not day_df.empty and 'eventName' in day_df.columns and 'pageTitle' in day_df.columns:
        evt_df = day_df[day_df['pageTitle'].notna() & (day_df['pageTitle'] != '(not set)')]

        pv_df = evt_df[evt_df['eventName'] == 'page_view'].groupby('pageTitle')['eventCount'].sum().rename('page_view')
        cl_df = evt_df[evt_df['eventName'] == 'click'].groupby('pageTitle')['eventCount'].sum().rename('click')

        entry_df = pd.concat([pv_df, cl_df], axis=1).fillna(0).reset_index()
        entry_df['진입률(click/pv)'] = entry_df.apply(
            lambda r: (r['click'] / r['page_view'] * 100) if r['page_view'] > 0 else 0, axis=1
        )
        entry_df = entry_df[entry_df['page_view'] > 0].sort_values('page_view', ascending=False).head(20)

        if not entry_df.empty:
            col_l, col_r = st.columns(2)
            with col_l:
                fig_entry = go.Figure()
                fig_entry.add_trace(go.Bar(
                    y=entry_df['pageTitle'], x=entry_df['page_view'],
                    name='Page View', orientation='h',
                    marker_color=PASTEL['teal']
                ))
                fig_entry.add_trace(go.Bar(
                    y=entry_df['pageTitle'], x=entry_df['click'],
                    name='Click', orientation='h',
                    marker_color=PASTEL['yellow']
                ))
                layout_e = dict(**CHART_LAYOUT)
                layout_e['barmode'] = 'group'
                layout_e['height'] = 420
                layout_e['xaxis'] = dict(title='이벤트 수', showgrid=True, gridcolor='rgba(128,128,128,0.12)')
                layout_e['yaxis'] = dict(tickfont=dict(size=9), autorange='reversed')
                layout_e['margin'] = dict(t=15, b=30, l=160, r=15)
                fig_entry.update_layout(**layout_e)
                st.plotly_chart(fig_entry, width='stretch')

            with col_r:
                fig_ratio = px.scatter(
                    entry_df, x='page_view', y='진입률(click/pv)',
                    size='click', color='pageTitle',
                    text='pageTitle', size_max=40,
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    labels={'page_view': 'Page View', '진입률(click/pv)': '진입률 (%)'}
                )
                layout_r = dict(**CHART_LAYOUT)
                layout_r['height'] = 420
                layout_r['showlegend'] = False
                layout_r['hovermode'] = 'closest'
                fig_ratio.update_traces(textposition='top center', textfont_size=8)
                fig_ratio.update_layout(**layout_r)
                st.plotly_chart(fig_ratio, width='stretch')
        else:
            st.info("기준일의 page_view / click 이벤트 데이터가 없습니다.")
    else:
        st.info("eventName 또는 pageTitle 컬럼이 없어 진입률을 계산할 수 없습니다.")

    st.divider()

    # ── 섹션 3: 페이지별 평균 세션시간 ──────────────────────────────
    st.markdown("## 페이지별 평균 세션시간")

    if not day_df.empty and 'pageTitle' in day_df.columns and 'averageSessionDuration' in day_df.columns:
        dur_df = day_df[
            day_df['pageTitle'].notna() & (day_df['pageTitle'] != '(not set)')
        ].groupby('pageTitle').agg(
            평균세션시간=('averageSessionDuration', 'mean'),
            세션수=('sessions', 'sum')
        ).reset_index()
        dur_df = dur_df[dur_df['세션수'] > 0].sort_values('평균세션시간', ascending=False).head(20)

        if not dur_df.empty:
            col_l2, col_r2 = st.columns([3, 2])
            with col_l2:
                fig_dur = go.Figure(go.Bar(
                    x=dur_df['평균세션시간'],
                    y=dur_df['pageTitle'],
                    orientation='h',
                    marker=dict(
                        color=dur_df['평균세션시간'],
                        colorscale=[[0, PASTEL['teal']], [1, '#22D3EE']],
                        showscale=False
                    ),
                    text=dur_df['평균세션시간'].apply(lambda v: f"{v:.0f}초"),
                    textposition='outside'
                ))
                layout_d = dict(**CHART_LAYOUT)
                layout_d['height'] = 420
                layout_d['xaxis'] = dict(title='평균 세션시간 (초)', showgrid=True, gridcolor='rgba(128,128,128,0.12)')
                layout_d['yaxis'] = dict(tickfont=dict(size=9), autorange='reversed')
                layout_d['margin'] = dict(t=15, b=30, l=160, r=60)
                fig_dur.update_layout(**layout_d)
                st.plotly_chart(fig_dur, width='stretch')

            with col_r2:
                fig_scatter = px.scatter(
                    dur_df, x='세션수', y='평균세션시간',
                    text='pageTitle', size='세션수',
                    size_max=30,
                    color='평균세션시간',
                    color_continuous_scale=['#4DB8A4', '#22D3EE'],
                    labels={'세션수': '세션 수', '평균세션시간': '평균 세션시간 (초)'}
                )
                layout_s = dict(**CHART_LAYOUT)
                layout_s['height'] = 420
                layout_s['showlegend'] = False
                layout_s['hovermode'] = 'closest'
                layout_s['coloraxis_showscale'] = False
                fig_scatter.update_traces(textposition='top center', textfont_size=8)
                fig_scatter.update_layout(**layout_s)
                st.plotly_chart(fig_scatter, width='stretch')
        else:
            st.info("세션시간 데이터가 없습니다.")
    else:
        st.info("pageTitle 또는 averageSessionDuration 컬럼이 없습니다.")

    st.divider()

    # ── 섹션 4: 이벤트 유형별 분포 (기준일) ────────────────────────
    st.markdown("## 이벤트 유형 분포 (기준일)")

    if not day_df.empty and 'eventName' in day_df.columns:
        evt_sum = day_df.groupby('eventName')['eventCount'].sum().reset_index()
        evt_sum = evt_sum[evt_sum['eventCount'] > 0].sort_values('eventCount', ascending=False).head(15)

        if not evt_sum.empty:
            col_e1, col_e2 = st.columns([2, 3])
            with col_e1:
                fig_donut = go.Figure(go.Pie(
                    labels=evt_sum['eventName'],
                    values=evt_sum['eventCount'],
                    hole=0.5,
                    textinfo='label+percent',
                    textfont_size=9,
                    marker_colors=px.colors.qualitative.Pastel
                ))
                layout_do = dict(**CHART_LAYOUT)
                layout_do['height'] = 320
                layout_do['showlegend'] = False
                layout_do['margin'] = dict(t=15, b=15, l=15, r=15)
                fig_donut.update_layout(**layout_do)
                st.plotly_chart(fig_donut, width='stretch')

            with col_e2:
                fig_evt = go.Figure(go.Bar(
                    x=evt_sum['eventCount'],
                    y=evt_sum['eventName'],
                    orientation='h',
                    marker_color=PASTEL['teal'],
                    text=evt_sum['eventCount'].apply(lambda v: f"{int(v):,}"),
                    textposition='outside'
                ))
                layout_ev = dict(**CHART_LAYOUT)
                layout_ev['height'] = 320
                layout_ev['xaxis'] = dict(title='이벤트 수', showgrid=True, gridcolor='rgba(128,128,128,0.12)')
                layout_ev['yaxis'] = dict(tickfont=dict(size=9), autorange='reversed')
                layout_ev['margin'] = dict(t=15, b=30, l=140, r=60)
                fig_evt.update_layout(**layout_ev)
                st.plotly_chart(fig_evt, width='stretch')
        else:
            st.info("이벤트 데이터가 없습니다.")
