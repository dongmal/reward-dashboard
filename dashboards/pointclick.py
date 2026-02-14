"""포인트클릭 대시보드"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import (
    safe_divide, get_comparison_metrics, make_weekly,
    format_won, format_number, format_pct,
    apply_layout, set_y_korean_ticks, week_label, quick_date_picker
)
from config.constants import PASTEL, PUB_COLORS


def render_pointclick_dashboard(df: pd.DataFrame):
    """포인트클릭 대시보드 렌더링"""
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
        kf, kt = quick_date_picker(dmin, dmax, "pc_kpi", "어제")
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

    @st.fragment
    def pc_detail_section():
        st.markdown("## 🔎 상세 분석")
        kf, kt = quick_date_picker(dmin, dmax, "pc_detail", "전주")
        kdf = f[(f['date'].dt.date >= kf) & (f['date'].dt.date <= kt)]
        st.caption(f"📅 {kf} ~ {kt}")

        if kdf.empty:
            st.info("선택한 기간에 데이터가 없습니다.")
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
        tf, tt = quick_date_picker(dmin, dmax, "pc_tr", "이전달1일")
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
    st.markdown("---")
    pc_detail_section()
    st.markdown("---")
    pc_trend_section()
