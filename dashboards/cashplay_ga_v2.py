"""캐시플레이 GA4 심화 대시보드 v2
섹션 1 – WoW 비교 & 일별 트렌드    : 전기간 대비 델타 카드 + 일별 세션·사용자 + 전기간 오버레이
섹션 2 – 스티키니스 & 참여 품질     : DAU/MAU, 1인당 세션, 참여율 7일 이평
섹션 3 – 버튼 클릭 & 행동 흐름      : button_id 클릭수 Treemap + 날짜별 클릭 Top5 트렌드
섹션 4 – 커스텀 페이지 심화          : ev_page × 날짜 히트맵 + 세션×참여율 버블차트
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
    if prev == 0:
        return None
    d = safe_divide(curr - prev, prev, default=0, scale=100)
    return f"{'+'if d>=0 else ''}{d:.1f}%"


def _col_norm(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for c in df.columns:
        if c == 'customEvent:page':        rename[c] = 'ev_page'
        elif c == 'customEvent:page_type': rename[c] = 'ev_page_type'
        elif c == 'customEvent:button_id': rename[c] = 'ev_button_id'
    return df.rename(columns=rename) if rename else df


# ── 메인 렌더 ──────────────────────────────────────────────
def render_cashplay_ga_v2_dashboard(df: pd.DataFrame):
    if df.empty:
        st.warning("캐시플레이 GA4 데이터가 없습니다.")
        return
    try:
        df['date'] = pd.to_datetime(df['date'])
        dmin, dmax = df['date'].min().date(), df['date'].max().date()
    except Exception:
        st.error("날짜 데이터를 처리할 수 없습니다.")
        return

    df = _col_norm(df)

    # ── 섹션 1 : WoW 비교 & 일별 트렌드 ─────────────────────
    @st.fragment
    def section_weekly():
        st.markdown("## 📈 WoW 비교 & 일별 트렌드")
        f, t = quick_date_picker(dmin, dmax, "cp_v2_weekly", "이번달")
        fdf = df[(df['date'].dt.date >= f) & (df['date'].dt.date <= t)]
        if fdf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
            return

        span = (t - f).days + 1
        pf, pt = f - timedelta(days=span), f - timedelta(days=1)
        pdf = df[(df['date'].dt.date >= pf) & (df['date'].dt.date <= pt)]

        def agg(d):
            return d.groupby('date').agg(
                sessions=('sessions','sum'),
                activeUsers=('activeUsers','sum'),
                newUsers=('newUsers','sum'),
                eventCount=('eventCount','sum'),
                engagementRate=('engagementRate','mean'),
                userEngagementDuration=('userEngagementDuration','sum'),
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
        k1.metric("세션 수",     format_number(c_sess), _wow_delta(c_sess, p_sess))
        k2.metric("활성 사용자", format_number(c_dau),  _wow_delta(c_dau,  p_dau))
        k3.metric("신규 사용자", format_number(c_new),  _wow_delta(c_new,  p_new))
        k4.metric("평균 참여율", f"{c_eng:.1f}%",       _wow_delta(c_eng,  p_eng))
        k5.metric("총 참여시간", f"{c_edur/3600:.1f}h", _wow_delta(c_edur, p_edur))
        st.caption(f"△ 직전 동기간({pf} ~ {pt}) 대비")
        st.markdown("---")

        # 일별 세션(바) + DAU(선) + 전기간 오버레이
        st.markdown("#### 일별 세션 & 활성 사용자 (전기간 비교)")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=cur['date'], y=cur['sessions'],
            name='세션수', marker_color=PASTEL['blue'], opacity=0.55,
            hovertemplate="세션: %{y:,.0f}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=cur['date'], y=cur['activeUsers'],
            name='DAU', mode='lines+markers',
            line=dict(color=PASTEL['orange'], width=2.5), marker=dict(size=6),
            yaxis='y2',
            hovertemplate="DAU: %{y:,.0f}<extra></extra>"
        ))
        if not prv.empty:
            prv_s = prv.copy()
            prv_s['date'] = prv_s['date'] + timedelta(days=span)
            fig.add_trace(go.Scatter(
                x=prv_s['date'], y=prv_s['sessions'],
                name='전기간 세션', mode='lines',
                line=dict(color=PASTEL['gray'], width=1.5, dash='dot'), opacity=0.6,
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

        # 신규 vs 재방문 스택 + 신규 비율 선
        st.markdown("#### 신규 vs 재방문 & 신규 비율")
        cur['returning'] = (cur['activeUsers'] - cur['newUsers']).clip(lower=0)
        cur['new_rate']  = cur.apply(
            lambda r: safe_divide(r['newUsers'], r['activeUsers'], default=0, scale=100), axis=1
        )
        col1, col2 = st.columns(2)
        with col1:
            fig_s = go.Figure()
            fig_s.add_trace(go.Bar(
                x=cur['date'], y=cur['newUsers'],
                name='신규', marker_color=PASTEL['orange'], opacity=0.8,
                hovertemplate="신규: %{y:,.0f}<extra></extra>"
            ))
            fig_s.add_trace(go.Bar(
                x=cur['date'], y=cur['returning'],
                name='재방문', marker_color=PASTEL['teal'], opacity=0.8,
                hovertemplate="재방문: %{y:,.0f}<extra></extra>"
            ))
            apply_layout(fig_s, dict(height=280, barmode='stack', hovermode='x unified'))
            st.plotly_chart(fig_s, use_container_width=True)
        with col2:
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatter(
                x=cur['date'], y=cur['new_rate'],
                name='신규 비율', mode='lines',
                line=dict(color=PASTEL['orange'], width=2),
                fill='tozeroy', fillcolor='rgba(237,125,49,0.08)',
                hovertemplate="신규 비율: %{y:.1f}%<extra></extra>"
            ))
            fig_r.add_trace(go.Scatter(
                x=cur['date'], y=cur['engagementRate'],
                name='참여율', mode='lines',
                line=dict(color=PASTEL['blue'], width=2, dash='dash'),
                hovertemplate="참여율: %{y:.1f}%<extra></extra>"
            ))
            apply_layout(fig_r, dict(height=280, hovermode='x unified',
                yaxis=dict(ticksuffix='%')))
            st.plotly_chart(fig_r, use_container_width=True)

        # 총 참여시간 + 7일 이평
        st.markdown("#### 일별 총 참여시간 & 7일 이동평균")
        fig_e = go.Figure()
        fig_e.add_trace(go.Bar(
            x=cur['date'], y=cur['userEngagementDuration'],
            marker_color=PASTEL['purple'], opacity=0.6,
            hovertemplate="참여시간: %{y:,.0f}초<extra></extra>"
        ))
        fig_e.add_trace(go.Scatter(
            x=cur['date'],
            y=cur['userEngagementDuration'].rolling(7, min_periods=1).mean(),
            name='7일 이평', mode='lines',
            line=dict(color=PASTEL['red'], width=2.5),
            hovertemplate="7일 이평: %{y:,.0f}초<extra></extra>"
        ))
        apply_layout(fig_e, dict(height=260, hovermode='x unified'))
        st.plotly_chart(fig_e, use_container_width=True)

    # ── 섹션 2 : 스티키니스 & 참여 품질 ────────────────────
    @st.fragment
    def section_stickiness():
        st.markdown("## 🧲 스티키니스 & 참여 품질")
        f, t = quick_date_picker(dmin, dmax, "cp_v2_sticky", "이번달")
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

        daily['dau_mau']       = daily.apply(lambda r: safe_divide(r['dau'], r['mau'], default=0, scale=100), axis=1)
        daily['dau_wau']       = daily.apply(lambda r: safe_divide(r['dau'], r['wau'], default=0, scale=100), axis=1)
        daily['sess_per_user'] = daily.apply(lambda r: safe_divide(r['sessions'], r['dau'], default=0, scale=1), axis=1)

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("DAU/MAU", f"{daily['dau_mau'].mean():.1f}%",
                  help="높을수록 매일 복귀하는 충성 사용자 비중 높음")
        k2.metric("DAU/WAU", f"{daily['dau_wau'].mean():.1f}%")
        k3.metric("세션/사용자", f"{daily['sess_per_user'].mean():.2f}")
        k4.metric("평균 세션타임", f"{daily['avgDuration'].mean():.0f}초")
        k5.metric("평균 참여율", f"{daily['engagementRate'].mean():.1f}%")
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### DAU/MAU & DAU/WAU 추이")
            fig_k = go.Figure()
            fig_k.add_trace(go.Scatter(
                x=daily['date'], y=daily['dau_mau'], name='DAU/MAU',
                mode='lines', line=dict(color=PASTEL['purple'], width=2),
                fill='tozeroy', fillcolor='rgba(168,85,247,0.07)',
                hovertemplate="DAU/MAU: %{y:.1f}%<extra></extra>"
            ))
            fig_k.add_trace(go.Scatter(
                x=daily['date'], y=daily['dau_wau'], name='DAU/WAU',
                mode='lines', line=dict(color=PASTEL['blue'], width=2, dash='dash'),
                hovertemplate="DAU/WAU: %{y:.1f}%<extra></extra>"
            ))
            apply_layout(fig_k, dict(height=300, hovermode='x unified',
                yaxis=dict(ticksuffix='%')))
            st.plotly_chart(fig_k, use_container_width=True)

        with col2:
            st.markdown("#### 참여율 + 7일 이평 & 세션타임")
            fig_q = go.Figure()
            fig_q.add_trace(go.Scatter(
                x=daily['date'], y=daily['engagementRate'], name='참여율(%)',
                mode='lines+markers', line=dict(color=PASTEL['green'], width=2),
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
                x=daily['date'], y=daily['avgDuration'], name='세션타임(초)',
                mode='lines', line=dict(color=PASTEL['red'], width=2),
                yaxis='y2',
                hovertemplate="세션타임: %{y:.0f}초<extra></extra>"
            ))
            max_d = daily['avgDuration'].max() if not daily.empty else 100
            apply_layout(fig_q, dict(
                height=300, hovermode='x unified',
                yaxis=dict(ticksuffix='%'),
                yaxis2=dict(overlaying='y', side='right',
                    range=[0, max(max_d*1.3, 60)],
                    ticksuffix='초', gridcolor='rgba(0,0,0,0)',
                    tickfont=dict(color=PASTEL['red']))
            ))
            st.plotly_chart(fig_q, use_container_width=True)

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
        apply_layout(fig_su, dict(height=250, hovermode='x unified'))
        st.plotly_chart(fig_su, use_container_width=True)

    # ── 섹션 3 : 버튼 클릭 & 행동 흐름 ─────────────────────
    @st.fragment
    def section_button():
        st.markdown("## 🖱️ 버튼 클릭 & 행동 흐름")
        f, t = quick_date_picker(dmin, dmax, "cp_v2_button", "이번달")
        fdf = df[(df['date'].dt.date >= f) & (df['date'].dt.date <= t)]
        if fdf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
            return
        st.caption(f"📅 {f} ~ {t}")

        if 'ev_button_id' not in fdf.columns:
            st.info("버튼 클릭 데이터(customEvent:button_id)가 없습니다.")
            return

        btn = (
            fdf.groupby('ev_button_id', dropna=False)
            .agg(clicks=('eventCount','sum'), users=('activeUsers','sum'), sessions=('sessions','sum'))
            .reset_index()
        )
        btn = btn[~btn['ev_button_id'].astype(str)
                  .str.contains(r'^\(not set\)$|^$', case=False, na=False, regex=True)]
        btn = btn.sort_values('clicks', ascending=False)

        if btn.empty:
            st.info("버튼 클릭 기록이 없습니다.")
            return

        total_clicks = btn['clicks'].sum()
        btn['rate'] = btn['clicks'].apply(
            lambda x: safe_divide(x, total_clicks, default=0, scale=100)
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 버튼별 클릭 수 Treemap (Top 30)")
            top30 = btn.head(30)
            fig_tree = go.Figure(go.Treemap(
                labels=top30['ev_button_id'].astype(str),
                parents=[''] * len(top30),
                values=top30['clicks'],
                customdata=top30[['users','rate']].values,
                texttemplate="%{label}<br>%{value:,.0f}",
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "클릭: %{value:,.0f}<br>"
                    "사용자: %{customdata[0]:,.0f}<br>"
                    "비율: %{customdata[1]:.1f}%"
                    "<extra></extra>"
                ),
                marker=dict(
                    colorscale='Oranges',
                    colors=top30['rate'].tolist(),
                    showscale=True,
                    colorbar=dict(title='비율%', thickness=12)
                ),
                textfont=dict(size=10),
            ))
            apply_layout(fig_tree, dict(height=420, margin=dict(t=15,b=15,l=15,r=60)))
            st.plotly_chart(fig_tree, use_container_width=True)

        with col2:
            st.markdown("#### 버튼별 클릭수 Top 20 (수평 바)")
            top20 = btn.head(20)
            fig_bar = go.Figure(go.Bar(
                y=top20['ev_button_id'][::-1].astype(str),
                x=top20['clicks'][::-1],
                orientation='h',
                marker=dict(
                    color=top20['rate'][::-1],
                    colorscale='Oranges',
                    showscale=False,
                ),
                hovertemplate="%{y}: %{x:,.0f}회<extra></extra>"
            ))
            apply_layout(fig_bar, dict(
                height=420, showlegend=False,
                margin=dict(t=15, b=30, l=180, r=15)
            ))
            st.plotly_chart(fig_bar, use_container_width=True)

        # 일별 Top5 버튼 트렌드
        st.markdown("#### 일별 Top 5 버튼 클릭 트렌드")
        top5_btns = btn.head(5)['ev_button_id'].tolist()
        daily_btn = (
            fdf[fdf['ev_button_id'].isin(top5_btns)]
            .groupby(['date','ev_button_id'], dropna=False)['eventCount']
            .sum().reset_index()
        )
        if not daily_btn.empty:
            fig_line = go.Figure()
            for i, b in enumerate(top5_btns):
                bd = daily_btn[daily_btn['ev_button_id'] == b]
                if not bd.empty:
                    fig_line.add_trace(go.Scatter(
                        x=bd['date'], y=bd['eventCount'],
                        name=str(b), mode='lines+markers',
                        line=dict(color=PUB_COLORS[i % len(PUB_COLORS)], width=2),
                        marker=dict(size=5),
                        hovertemplate=f"{b}: %{{y:,.0f}}회<extra></extra>"
                    ))
            apply_layout(fig_line, dict(height=300, hovermode='x unified'))
            st.plotly_chart(fig_line, use_container_width=True)

        # 전체 테이블
        st.markdown("#### 전체 버튼 클릭 통계")
        disp = btn.copy()
        disp['clicks']  = disp['clicks'].apply(lambda x: f"{x:,.0f}")
        disp['users']   = disp['users'].apply(lambda x: f"{x:,.0f}")
        disp['sessions']= disp['sessions'].apply(lambda x: f"{x:,.0f}")
        disp['rate']    = disp['rate'].apply(lambda x: f"{x:.1f}")
        disp.columns = ['버튼 ID','클릭수','사용자수','세션수','클릭비율(%)']
        st.dataframe(disp, use_container_width=True, hide_index=True, height=360)
        csv = btn.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 CSV 다운로드", csv,
            file_name=f"CP_버튼클릭_{f}_{t}.csv", mime="text/csv")

    # ── 섹션 4 : 커스텀 페이지 심화 ─────────────────────────
    @st.fragment
    def section_page():
        st.markdown("## 📱 커스텀 페이지 심화 분석")
        f, t = quick_date_picker(dmin, dmax, "cp_v2_page", "이번달")
        fdf = df[(df['date'].dt.date >= f) & (df['date'].dt.date <= t)]
        if fdf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
            return
        st.caption(f"📅 {f} ~ {t}")

        page_col = 'ev_page' if 'ev_page' in fdf.columns else (
                   'pageTitle' if 'pageTitle' in fdf.columns else None)
        if not page_col:
            st.info("페이지 데이터가 없습니다.")
            return

        page_stats = (
            fdf.groupby(page_col, dropna=False)
            .agg(sessions=('sessions','sum'),
                 activeUsers=('activeUsers','sum'),
                 eventCount=('eventCount','sum'),
                 engagementRate=('engagementRate','mean'),
                 avgDuration=('averageSessionDuration','mean'),
                 engDuration=('userEngagementDuration','sum'))
            .reset_index()
        )
        page_stats = page_stats[
            ~page_stats[page_col].astype(str)
             .str.contains(r'^\(not set\)$|^$', case=False, na=False, regex=True)
        ].sort_values('sessions', ascending=False)
        top15 = page_stats.head(15)
        top20 = page_stats.head(20)

        # 버블차트 : x=세션, y=참여율, size=참여시간, color=참여율
        st.markdown("#### 페이지 성과 버블차트 (세션 × 참여율 × 참여시간)")
        bsize = (top15['engDuration'] / max(top15['engDuration'].max(), 1) * 55 + 8).clip(lower=8)
        fig_b = go.Figure()
        for idx, row in top15.iterrows():
            fig_b.add_trace(go.Scatter(
                x=[row['sessions']], y=[row['engagementRate']],
                mode='markers+text',
                text=[str(row[page_col])[:20]],
                textposition='top center', textfont=dict(size=9),
                marker=dict(
                    size=float(bsize.loc[idx]),
                    color=row['engagementRate'],
                    colorscale='Teal', cmin=0, cmax=100,
                    showscale=(idx == top15.index[0]),
                    colorbar=dict(title='참여율%', thickness=12, len=0.7, x=1.02)
                                 if idx == top15.index[0] else None,
                    line=dict(width=1, color='rgba(0,0,0,0.15)')
                ),
                hovertemplate=(
                    f"<b>{row[page_col]}</b><br>"
                    "세션: %{x:,.0f}<br>참여율: %{y:.1f}%<br>"
                    f"참여시간: {row['engDuration']:,.0f}초<br>"
                    f"세션타임: {row['avgDuration']:.0f}초"
                    "<extra></extra>"
                ),
                name=str(row[page_col])
            ))
        apply_layout(fig_b, dict(
            height=400, showlegend=False,
            xaxis=dict(title='세션 수'),
            yaxis=dict(title='참여율(%)', ticksuffix='%'),
            margin=dict(t=15, b=40, l=55, r=80)
        ))
        st.plotly_chart(fig_b, use_container_width=True)

        # 페이지 × 날짜 히트맵 (eventCount 기준)
        st.markdown("#### 페이지별 일별 이벤트 히트맵 (Top 15)")
        heat_pages = top15[page_col].tolist()
        heat_df = fdf[fdf[page_col].isin(heat_pages)].copy()
        pivot = (
            heat_df.groupby([page_col,'date'])['eventCount'].sum()
            .reset_index()
            .pivot(index=page_col, columns='date', values='eventCount')
            .fillna(0)
        )
        pivot.columns = [str(c.date()) if hasattr(c,'date') else str(c) for c in pivot.columns]
        # 행 순서 유지
        try:
            pivot = pivot.loc[heat_pages]
        except Exception:
            pass

        fig_heat = go.Figure(go.Heatmap(
            z=pivot.values,
            x=list(pivot.columns),
            y=list(pivot.index),
            colorscale='Teal',
            hovertemplate="날짜: %{x}<br>페이지: %{y}<br>이벤트: %{z:,.0f}<extra></extra>",
            colorbar=dict(title='이벤트수', thickness=12, len=0.8)
        ))
        apply_layout(fig_heat, dict(
            height=min(80 + len(heat_pages) * 36, 500),
            xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=9)),
            yaxis=dict(showgrid=False, tickfont=dict(size=9)),
            margin=dict(t=15, b=55, l=180, r=80)
        ))
        st.plotly_chart(fig_heat, use_container_width=True)

        # Treemap : 페이지별 총 참여시간
        st.markdown("#### 페이지별 총 참여시간 Treemap (Top 30)")
        top30 = page_stats.head(30)
        fig_tree = go.Figure(go.Treemap(
            labels=top30[page_col].astype(str),
            parents=[''] * len(top30),
            values=top30['engDuration'],
            customdata=top30[['sessions','engagementRate','avgDuration']].values,
            texttemplate="%{label}<br>%{value:,.0f}초",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "참여시간: %{value:,.0f}초<br>"
                "세션: %{customdata[0]:,.0f}<br>"
                "참여율: %{customdata[1]:.1f}%<br>"
                "세션타임: %{customdata[2]:.0f}초"
                "<extra></extra>"
            ),
            marker=dict(colorscale='Teal',
                        colors=top30['engagementRate'].tolist(),
                        showscale=True,
                        colorbar=dict(title='참여율%', thickness=12)),
            textfont=dict(size=11),
        ))
        apply_layout(fig_tree, dict(height=400, margin=dict(t=15,b=15,l=15,r=15)))
        st.plotly_chart(fig_tree, use_container_width=True)

        # 테이블
        st.markdown("#### 전체 페이지 통계")
        disp = page_stats.rename(columns={
            page_col:'페이지','sessions':'세션수','activeUsers':'활성사용자',
            'eventCount':'이벤트수','engagementRate':'참여율(%)',
            'avgDuration':'평균세션타임(초)','engDuration':'총참여시간(초)'
        }).copy()
        for c in ['세션수','활성사용자','이벤트수','총참여시간(초)']:
            disp[c] = disp[c].apply(lambda x: f"{x:,.0f}")
        disp['참여율(%)']       = disp['참여율(%)'].apply(lambda x: f"{x:.1f}")
        disp['평균세션타임(초)'] = disp['평균세션타임(초)'].apply(lambda x: f"{x:.1f}")
        st.dataframe(disp, use_container_width=True, hide_index=True, height=380)
        csv = page_stats.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 CSV 다운로드", csv,
            file_name=f"CP_페이지분석_{f}_{t}.csv", mime="text/csv")

    section_weekly()
    st.markdown("---")
    section_stickiness()
    st.markdown("---")
    section_button()
    st.markdown("---")
    section_page()
