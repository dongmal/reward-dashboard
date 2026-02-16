"""포인트클릭 GA4 심화 대시보드 v2
섹션 1 – 주간 트렌드 & WoW 비교   : 핵심 지표 전주 대비 델타 카드 + 주별 세션·DAU 추이
섹션 2 – 스티키니스 & 유지율       : DAU/WAU, DAU/MAU, WAU/MAU 비율 + 7일 이동평균 참여율
섹션 3 – 매체별 성과 트렌드        : 매체 Top 10 주차별 세션 히트맵 + 매체별 참여율 버블차트
섹션 4 – 페이지 경로 심화           : 경로별 참여시간 산점도(세션수×참여율) + pagePath Treemap
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta
from utils import (
    safe_divide, format_number, format_pct,
    apply_layout, quick_date_picker
)
from config.constants import PASTEL, PUB_COLORS


# ── 내부 헬퍼 ──────────────────────────────────────────────
def _wow_delta(curr, prev):
    """전주 대비 증감률 문자열 반환"""
    if prev == 0:
        return None
    d = safe_divide(curr - prev, prev, default=0, scale=100)
    sign = "+" if d >= 0 else ""
    return f"{sign}{d:.1f}%"


def _col_norm(df: pd.DataFrame) -> pd.DataFrame:
    """customEvent:* 컬럼명 정규화 + media_name fallback"""
    rename = {}
    for c in df.columns:
        if c == 'customEvent:page_name':   rename[c] = 'ev_page_name'
        elif c == 'customEvent:page_type': rename[c] = 'ev_page_type'
        elif c == 'customEvent:media_key': rename[c] = 'ev_media_key'
    if rename:
        df = df.rename(columns=rename)
    if 'media_name' not in df.columns:
        df['media_name'] = df['ev_media_key'] if 'ev_media_key' in df.columns else '(unknown)'
    return df


# ── 메인 렌더 ──────────────────────────────────────────────
def render_pointclick_ga_v2_dashboard(df: pd.DataFrame):
    if df.empty:
        st.warning("포인트클릭 GA4 데이터가 없습니다.")
        return
    try:
        df['date'] = pd.to_datetime(df['date'])
        dmin, dmax = df['date'].min().date(), df['date'].max().date()
    except Exception:
        st.error("날짜 데이터를 처리할 수 없습니다.")
        return

    df = _col_norm(df)

    # ── 섹션 1 : 주간 트렌드 & WoW 비교 ────────────────────
    @st.fragment
    def section_weekly():
        st.markdown("## 📈 주간 트렌드 & WoW 비교")
        f, t = quick_date_picker(dmin, dmax, "pc_v2_weekly", "이번달")
        fdf = df[(df['date'].dt.date >= f) & (df['date'].dt.date <= t)]
        if fdf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
            return

        # 현재 기간 vs 직전 동일 기간
        span = (t - f).days + 1
        pf, pt = f - timedelta(days=span), f - timedelta(days=1)
        pdf = df[(df['date'].dt.date >= pf) & (df['date'].dt.date <= pt)]

        def agg(d): return d.groupby('date').agg(
            sessions=('sessions', 'sum'),
            activeUsers=('activeUsers', 'sum'),
            newUsers=('newUsers', 'sum'),
            eventCount=('eventCount', 'sum'),
            engagementRate=('engagementRate', 'mean'),
            userEngagementDuration=('userEngagementDuration', 'sum'),
        ).reset_index()

        cur = agg(fdf)
        prv = agg(pdf)

        c_sess = int(cur['sessions'].sum())
        c_dau  = int(cur['activeUsers'].sum())
        c_new  = int(cur['newUsers'].sum())
        c_eng  = cur['engagementRate'].mean()
        c_edur = cur['userEngagementDuration'].sum()

        p_sess = int(prv['sessions'].sum()) if not prv.empty else 0
        p_dau  = int(prv['activeUsers'].sum()) if not prv.empty else 0
        p_new  = int(prv['newUsers'].sum()) if not prv.empty else 0
        p_eng  = prv['engagementRate'].mean() if not prv.empty else 0
        p_edur = prv['userEngagementDuration'].sum() if not prv.empty else 0

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("세션 수",      format_number(c_sess), _wow_delta(c_sess, p_sess))
        k2.metric("활성 사용자",  format_number(c_dau),  _wow_delta(c_dau,  p_dau))
        k3.metric("신규 사용자",  format_number(c_new),  _wow_delta(c_new,  p_new))
        k4.metric("평균 참여율",  f"{c_eng:.1f}%",       _wow_delta(c_eng,  p_eng))
        k5.metric("총 참여시간",  f"{c_edur/3600:.1f}h", _wow_delta(c_edur, p_edur))

        st.caption(f"△ 직전 동기간({pf} ~ {pt}) 대비")
        st.markdown("---")

        # 일별 세션 + 활성사용자 복합 차트
        st.markdown("#### 일별 세션 수 & 활성 사용자 추이")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=cur['date'], y=cur['sessions'],
            name='세션수', marker_color=PASTEL['blue'], opacity=0.55,
            hovertemplate="세션: %{y:,.0f}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=cur['date'], y=cur['activeUsers'],
            name='활성 사용자', mode='lines+markers',
            line=dict(color=PASTEL['orange'], width=2.5),
            marker=dict(size=6),
            yaxis='y2',
            hovertemplate="DAU: %{y:,.0f}<extra></extra>"
        ))
        # 이전 기간 세션 오버레이
        if not prv.empty:
            # 날짜를 현재 기간 기준으로 shift
            prv_shifted = prv.copy()
            prv_shifted['date'] = prv_shifted['date'] + timedelta(days=span)
            fig.add_trace(go.Scatter(
                x=prv_shifted['date'], y=prv_shifted['sessions'],
                name='전기간 세션', mode='lines',
                line=dict(color=PASTEL['gray'], width=1.5, dash='dot'),
                opacity=0.6,
                hovertemplate="전기간 세션: %{y:,.0f}<extra></extra>"
            ))
        max_dau = cur['activeUsers'].max() if not cur.empty else 100
        apply_layout(fig, dict(
            height=340, hovermode='x unified',
            yaxis2=dict(overlaying='y', side='right',
                range=[0, max(max_dau * 1.4, 10)],
                gridcolor='rgba(0,0,0,0)',
                tickfont=dict(color=PASTEL['orange']))
        ))
        st.plotly_chart(fig, use_container_width=True)

        # 주차별 집계 막대
        st.markdown("#### 주차별 세션 & 신규 사용자")
        fdf2 = fdf.copy()
        fdf2['week'] = fdf2['date'].dt.to_period('W').apply(lambda x: x.start_time.date())
        weekly = fdf2.groupby('week').agg(
            sessions=('sessions','sum'),
            newUsers=('newUsers','sum'),
            activeUsers=('activeUsers','sum'),
        ).reset_index()
        weekly['week_label'] = weekly['week'].apply(
            lambda d: f"{d.month}/{d.day}~{(d + timedelta(days=6)).month}/{(d + timedelta(days=6)).day}"
        )
        fig_w = go.Figure()
        fig_w.add_trace(go.Bar(
            x=weekly['week_label'], y=weekly['sessions'],
            name='세션수', marker_color=PASTEL['blue'], opacity=0.7,
            hovertemplate="세션: %{y:,.0f}<extra></extra>"
        ))
        fig_w.add_trace(go.Bar(
            x=weekly['week_label'], y=weekly['newUsers'],
            name='신규 사용자', marker_color=PASTEL['green'], opacity=0.7,
            hovertemplate="신규: %{y:,.0f}<extra></extra>"
        ))
        apply_layout(fig_w, dict(height=300, barmode='group'))
        st.plotly_chart(fig_w, use_container_width=True)

    # ── 섹션 2 : 스티키니스 & 유지율 ───────────────────────
    @st.fragment
    def section_stickiness():
        st.markdown("## 🧲 스티키니스 & 참여 품질")
        f, t = quick_date_picker(dmin, dmax, "pc_v2_sticky", "이번달")
        fdf = df[(df['date'].dt.date >= f) & (df['date'].dt.date <= t)]
        if fdf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
            return

        daily = fdf.groupby('date').agg(
            dau=('activeUsers','sum'),
            wau=('active7DayUsers','sum'),
            mau=('active28DayUsers','sum'),
            sessions=('sessions','sum'),
            engagementRate=('engagementRate','mean'),
            avgDuration=('averageSessionDuration','mean'),
        ).reset_index()

        # 스티키니스 비율 계산
        daily['dau_mau'] = daily.apply(
            lambda r: safe_divide(r['dau'], r['mau'], default=0, scale=100), axis=1
        )
        daily['dau_wau'] = daily.apply(
            lambda r: safe_divide(r['dau'], r['wau'], default=0, scale=100), axis=1
        )
        daily['sess_per_user'] = daily.apply(
            lambda r: safe_divide(r['sessions'], r['dau'], default=0, scale=1), axis=1
        )

        avg_dau_mau = daily['dau_mau'].mean()
        avg_dau_wau = daily['dau_wau'].mean()
        avg_sess_u  = daily['sess_per_user'].mean()
        avg_dur     = daily['avgDuration'].mean()
        avg_eng     = daily['engagementRate'].mean()

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("DAU/MAU (스티키니스)", f"{avg_dau_mau:.1f}%",
                  help="높을수록 매일 돌아오는 충성 사용자 비율이 높음")
        k2.metric("DAU/WAU",  f"{avg_dau_wau:.1f}%")
        k3.metric("세션/사용자", f"{avg_sess_u:.2f}",
                  help="1인당 평균 세션 수")
        k4.metric("평균 세션타임", f"{avg_dur:.0f}초")
        k5.metric("평균 참여율", f"{avg_eng:.1f}%")

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### DAU/MAU 스티키니스 추이")
            fig_s = go.Figure()
            fig_s.add_trace(go.Scatter(
                x=daily['date'], y=daily['dau_mau'],
                name='DAU/MAU', mode='lines',
                line=dict(color=PASTEL['purple'], width=2),
                fill='tozeroy', fillcolor='rgba(168,85,247,0.08)',
                hovertemplate="DAU/MAU: %{y:.1f}%<extra></extra>"
            ))
            fig_s.add_trace(go.Scatter(
                x=daily['date'], y=daily['dau_wau'],
                name='DAU/WAU', mode='lines',
                line=dict(color=PASTEL['blue'], width=2, dash='dash'),
                hovertemplate="DAU/WAU: %{y:.1f}%<extra></extra>"
            ))
            apply_layout(fig_s, dict(height=300, hovermode='x unified',
                yaxis=dict(ticksuffix='%')))
            st.plotly_chart(fig_s, use_container_width=True)

        with col2:
            st.markdown("#### 참여율 & 평균 세션타임 트렌드")
            fig_q = go.Figure()
            fig_q.add_trace(go.Scatter(
                x=daily['date'], y=daily['engagementRate'],
                name='참여율(%)', mode='lines+markers',
                line=dict(color=PASTEL['green'], width=2),
                marker=dict(size=4),
                hovertemplate="참여율: %{y:.1f}%<extra></extra>"
            ))
            fig_q.add_trace(go.Scatter(
                x=daily['date'],
                y=daily['engagementRate'].rolling(7, min_periods=1).mean(),
                name='7일 이평', mode='lines',
                line=dict(color=PASTEL['green'], width=1.5, dash='dot'),
                hovertemplate="7일 이평: %{y:.1f}%<extra></extra>"
            ))
            fig_q.add_trace(go.Scatter(
                x=daily['date'], y=daily['avgDuration'],
                name='세션타임(초)', mode='lines',
                line=dict(color=PASTEL['red'], width=2),
                yaxis='y2',
                hovertemplate="세션타임: %{y:.0f}초<extra></extra>"
            ))
            max_d = daily['avgDuration'].max() if not daily.empty else 100
            apply_layout(fig_q, dict(
                height=300, hovermode='x unified',
                yaxis=dict(ticksuffix='%'),
                yaxis2=dict(overlaying='y', side='right',
                    range=[0, max(max_d * 1.3, 60)],
                    ticksuffix='초', gridcolor='rgba(0,0,0,0)',
                    tickfont=dict(color=PASTEL['red']))
            ))
            st.plotly_chart(fig_q, use_container_width=True)

        # 세션/사용자 추이
        st.markdown("#### 1인당 세션 수 추이")
        fig_su = go.Figure()
        fig_su.add_trace(go.Bar(
            x=daily['date'], y=daily['sess_per_user'],
            marker_color=PASTEL['teal'], opacity=0.7,
            hovertemplate="세션/사용자: %{y:.2f}<extra></extra>"
        ))
        fig_su.add_trace(go.Scatter(
            x=daily['date'],
            y=daily['sess_per_user'].rolling(7, min_periods=1).mean(),
            name='7일 이평', mode='lines',
            line=dict(color=PASTEL['orange'], width=2),
            hovertemplate="7일 이평: %{y:.2f}<extra></extra>"
        ))
        apply_layout(fig_su, dict(height=250, showlegend=True, hovermode='x unified'))
        st.plotly_chart(fig_su, use_container_width=True)

    # ── 섹션 3 : 매체별 성과 트렌드 ────────────────────────
    @st.fragment
    def section_media():
        st.markdown("## 📡 매체별 성과 트렌드")
        f, t = quick_date_picker(dmin, dmax, "pc_v2_media", "이번달")
        fdf = df[(df['date'].dt.date >= f) & (df['date'].dt.date <= t)]
        if fdf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
            return
        st.caption(f"📅 {f} ~ {t}")

        # 매체별 집계
        media_stats = (
            fdf.groupby('media_name', dropna=False)
            .agg(sessions=('sessions','sum'),
                 activeUsers=('activeUsers','sum'),
                 newUsers=('newUsers','sum'),
                 eventCount=('eventCount','sum'),
                 engagementRate=('engagementRate','mean'),
                 avgDuration=('averageSessionDuration','mean'),
                 engDuration=('userEngagementDuration','sum'))
            .reset_index()
        )
        media_stats = media_stats[
            ~media_stats['media_name'].astype(str)
             .str.contains(r'^\(not set\)$|^$', case=False, na=False, regex=True)
        ].sort_values('sessions', ascending=False)

        top10 = media_stats.head(10)

        # 버블 차트 : x=세션수, y=참여율, size=참여시간, color=신규사용자 비율
        st.markdown("#### 매체 성과 버블차트 (세션 × 참여율 × 참여시간)")
        top10 = top10.copy()
        top10['new_rate'] = top10.apply(
            lambda r: safe_divide(r['newUsers'], r['activeUsers'], default=0, scale=100), axis=1
        )
        bubble_size = (top10['engDuration'] / top10['engDuration'].max() * 60 + 8).clip(lower=8)

        fig_bubble = go.Figure()
        for i, row in top10.iterrows():
            fig_bubble.add_trace(go.Scatter(
                x=[row['sessions']],
                y=[row['engagementRate']],
                mode='markers+text',
                name=str(row['media_name']),
                text=[str(row['media_name'])],
                textposition='top center',
                textfont=dict(size=9),
                marker=dict(
                    size=float(bubble_size.loc[i]),
                    color=row['new_rate'],
                    colorscale='RdYlGn',
                    cmin=0, cmax=100,
                    showscale=(i == top10.index[0]),
                    colorbar=dict(title='신규비율%', thickness=12, len=0.7,
                                  x=1.02) if i == top10.index[0] else None,
                    line=dict(width=1, color='rgba(0,0,0,0.2)')
                ),
                hovertemplate=(
                    f"<b>{row['media_name']}</b><br>"
                    "세션: %{x:,.0f}<br>참여율: %{y:.1f}%<br>"
                    f"신규비율: {row['new_rate']:.1f}%<br>"
                    f"참여시간: {row['engDuration']:,.0f}초"
                    "<extra></extra>"
                )
            ))
        apply_layout(fig_bubble, dict(
            height=420, showlegend=False,
            xaxis=dict(title='세션 수', showgrid=True),
            yaxis=dict(title='참여율(%)', ticksuffix='%'),
            margin=dict(t=15, b=40, l=55, r=80)
        ))
        st.plotly_chart(fig_bubble, use_container_width=True)

        # 매체 Top 10 주차별 세션 히트맵
        st.markdown("#### 매체 Top 10 – 주차별 세션 히트맵")
        top10_names = top10['media_name'].tolist()
        heat_df = fdf[fdf['media_name'].isin(top10_names)].copy()
        heat_df['week'] = heat_df['date'].dt.to_period('W').apply(
            lambda x: f"{x.start_time.month}/{x.start_time.day}"
        )
        pivot = (
            heat_df.groupby(['media_name', 'week'])['sessions'].sum()
            .reset_index()
            .pivot(index='media_name', columns='week', values='sessions')
            .fillna(0)
        )
        # 행 순서: 총 세션 내림차순
        pivot = pivot.loc[top10_names]

        fig_heat = go.Figure(go.Heatmap(
            z=pivot.values,
            x=list(pivot.columns),
            y=list(pivot.index),
            colorscale='Blues',
            hovertemplate="주차: %{x}<br>매체: %{y}<br>세션: %{z:,.0f}<extra></extra>",
            colorbar=dict(title='세션수', thickness=12, len=0.8)
        ))
        apply_layout(fig_heat, dict(
            height=min(80 + len(top10_names) * 38, 480),
            xaxis=dict(showgrid=False, tickfont=dict(size=10)),
            yaxis=dict(showgrid=False, tickfont=dict(size=10)),
            margin=dict(t=15, b=40, l=140, r=80)
        ))
        st.plotly_chart(fig_heat, use_container_width=True)

        # 요약 테이블
        st.markdown("#### 전체 매체 통계")
        disp = media_stats.copy()
        disp['신규비율(%)'] = disp.apply(
            lambda r: f"{safe_divide(r['newUsers'], r['activeUsers'], default=0, scale=100):.1f}", axis=1
        )
        disp = disp.rename(columns={
            'media_name':'매체명','sessions':'세션수','activeUsers':'활성사용자',
            'newUsers':'신규사용자','eventCount':'이벤트수',
            'engagementRate':'참여율(%)','avgDuration':'평균세션타임(초)',
            'engDuration':'총참여시간(초)'
        })
        for c in ['세션수','활성사용자','신규사용자','이벤트수','총참여시간(초)']:
            disp[c] = disp[c].apply(lambda x: f"{x:,.0f}")
        disp['참여율(%)']     = disp['참여율(%)'].apply(lambda x: f"{x:.1f}")
        disp['평균세션타임(초)'] = disp['평균세션타임(초)'].apply(lambda x: f"{x:.1f}")
        st.dataframe(disp, use_container_width=True, hide_index=True, height=380)
        csv = media_stats.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 CSV 다운로드", csv,
            file_name=f"PC_매체분석_{f}_{t}.csv", mime="text/csv")

    # ── 섹션 4 : 페이지 경로 심화 ────────────────────────
    @st.fragment
    def section_page():
        st.markdown("## 🗺️ 페이지 경로 심화 분석")
        f, t = quick_date_picker(dmin, dmax, "pc_v2_page", "이번달")
        fdf = df[(df['date'].dt.date >= f) & (df['date'].dt.date <= t)]
        if fdf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
            return
        st.caption(f"📅 {f} ~ {t}")

        path_col = 'pagePath' if 'pagePath' in fdf.columns else None
        if not path_col:
            st.info("pagePath 데이터가 없습니다.")
            return

        path_stats = (
            fdf.groupby(path_col, dropna=False)
            .agg(sessions=('sessions','sum'),
                 activeUsers=('activeUsers','sum'),
                 engagementRate=('engagementRate','mean'),
                 avgDuration=('averageSessionDuration','mean'),
                 engDuration=('userEngagementDuration','sum'))
            .reset_index()
        )
        path_stats = path_stats[
            ~path_stats[path_col].astype(str)
             .str.contains(r'^\(not set\)$|^$', case=False, na=False, regex=True)
        ].sort_values('sessions', ascending=False)
        top20 = path_stats.head(20)

        # 산점도 : x=세션수, y=참여율, size=평균세션타임, color=참여율
        st.markdown("#### 페이지별 세션 × 참여율 산점도 (버블 = 평균세션타임)")
        dot_size = (top20['avgDuration'] / max(top20['avgDuration'].max(), 1) * 50 + 8).clip(lower=8)
        fig_dot = go.Figure()
        for idx, row in top20.iterrows():
            fig_dot.add_trace(go.Scatter(
                x=[row['sessions']],
                y=[row['engagementRate']],
                mode='markers+text',
                text=[str(row[path_col])[-30:]],  # 경로 마지막 30자
                textposition='top center',
                textfont=dict(size=8),
                marker=dict(
                    size=float(dot_size.loc[idx]),
                    color=row['engagementRate'],
                    colorscale='Teal',
                    cmin=0, cmax=100,
                    showscale=(idx == top20.index[0]),
                    colorbar=dict(title='참여율%', thickness=12, len=0.7,
                                  x=1.02) if idx == top20.index[0] else None,
                    line=dict(width=1, color='rgba(0,0,0,0.15)')
                ),
                hovertemplate=(
                    f"<b>{row[path_col]}</b><br>"
                    "세션: %{x:,.0f}<br>참여율: %{y:.1f}%<br>"
                    f"평균세션타임: {row['avgDuration']:.0f}초"
                    "<extra></extra>"
                ),
                name=str(row[path_col])
            ))
        apply_layout(fig_dot, dict(
            height=420, showlegend=False,
            xaxis=dict(title='세션 수'),
            yaxis=dict(title='참여율(%)', ticksuffix='%'),
            margin=dict(t=15, b=40, l=55, r=80)
        ))
        st.plotly_chart(fig_dot, use_container_width=True)

        # Treemap : 경로별 참여시간 비중
        st.markdown("#### 페이지 경로별 총 참여시간 Treemap (Top 30)")
        top30 = path_stats.head(30)
        fig_tree = go.Figure(go.Treemap(
            labels=top30[path_col].astype(str),
            parents=[''] * len(top30),
            values=top30['engDuration'],
            customdata=top30[['sessions','engagementRate','avgDuration']].values,
            texttemplate="%{label}<br>%{value:,.0f}초",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "참여시간: %{value:,.0f}초<br>"
                "세션: %{customdata[0]:,.0f}<br>"
                "참여율: %{customdata[1]:.1f}%<br>"
                "평균세션타임: %{customdata[2]:.0f}초"
                "<extra></extra>"
            ),
            marker=dict(colorscale='Blues',
                        colors=top30['engagementRate'].tolist(),
                        showscale=True,
                        colorbar=dict(title='참여율%', thickness=12)),
            textfont=dict(size=11),
        ))
        apply_layout(fig_tree, dict(
            height=420,
            margin=dict(t=15, b=15, l=15, r=15)
        ))
        st.plotly_chart(fig_tree, use_container_width=True)

        # 테이블
        st.markdown("#### 전체 페이지 경로 통계")
        disp = path_stats.rename(columns={
            path_col:'페이지 경로',
            'sessions':'세션수','activeUsers':'활성사용자',
            'engagementRate':'참여율(%)','avgDuration':'평균세션타임(초)',
            'engDuration':'총참여시간(초)'
        }).copy()
        for c in ['세션수','활성사용자','총참여시간(초)']:
            disp[c] = disp[c].apply(lambda x: f"{x:,.0f}")
        disp['참여율(%)']       = disp['참여율(%)'].apply(lambda x: f"{x:.1f}")
        disp['평균세션타임(초)'] = disp['평균세션타임(초)'].apply(lambda x: f"{x:.1f}")
        st.dataframe(disp, use_container_width=True, hide_index=True, height=380)
        csv = path_stats.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 CSV 다운로드", csv,
            file_name=f"PC_페이지경로_{f}_{t}.csv", mime="text/csv")

    section_weekly()
    st.markdown("---")
    section_stickiness()
    st.markdown("---")
    section_media()
    st.markdown("---")
    section_page()
