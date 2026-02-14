"""캐시플레이 대시보드"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import (
    safe_divide, get_comparison_metrics, make_weekly,
    format_won, format_number, format_pct,
    apply_layout, set_y_korean_ticks, week_label, quick_date_picker
)
from config.constants import PASTEL


def render_cashplay_dashboard(df: pd.DataFrame):
    """캐시플레이 대시보드 렌더링"""
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
        kf, kt = quick_date_picker(dmin, dmax, "cp_kpi", "어제")
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

    @st.fragment
    def cp_detail_section():
        st.markdown("## 🔎 상세 분석")
        kf, kt = quick_date_picker(dmin, dmax, "cp_detail", "전주")
        kdf = df[(df['date'].dt.date >= kf) & (df['date'].dt.date <= kt)]
        st.caption(f"📅 {kf} ~ {kt}")

        if kdf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
            return

        st.markdown("### 📊 매출 구성 분석")
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

        st.markdown("### 🌟 자사 서비스(포인트클릭) 기여도")
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

        st.markdown("### 📋 매출 상세")
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
        tf, tt = quick_date_picker(dmin, dmax, "cp_tr", "이전달1일")
        tdf = df[(df['date'].dt.date >= tf) & (df['date'].dt.date <= tt)]

        if not tdf.empty:
            w = make_weekly(tdf)
            if not w.empty:
                w['margin_rate'] = w.apply(lambda row: safe_divide(row['margin'], row['revenue_total'], default=0, scale=100), axis=1)
                w['wl'] = w['week'].apply(week_label)

                fig = go.Figure()
                fig.add_trace(go.Bar(x=w['wl'], y=w['revenue_total'], name='총 매출',
                    marker_color=PASTEL['blue'], opacity=0.75, hovertemplate="매출: %{y:,.0f}원<extra></extra>"))
                fig.add_trace(go.Bar(x=w['wl'], y=-w['cost_total'], name='매입(리워드)', marker_color=PASTEL['red'], opacity=0.75, customdata=w['cost_total'],
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
    st.markdown("---")
    cp_detail_section()
    st.markdown("---")
    cp_trend_section()
