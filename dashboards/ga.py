"""GA4 대시보드"""
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


def render_ga_dashboard(df_pc: pd.DataFrame, df_cp: pd.DataFrame):
    """GA4 대시보드 렌더링 (포인트클릭 + 캐시플레이)"""
    st.markdown("## 🚧 GA4 대시보드")
    st.info("준비중입니다. 포인트클릭과 캐시플레이 GA 데이터를 추가할 예정입니다.")

    # TODO: GA4 데이터 로드 및 시각화
    # - 포인트클릭 GA 데이터
    # - 캐시플레이 GA 데이터
    # - 통합 분석
