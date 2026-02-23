"""메트릭 계산 및 포맷팅 유틸리티"""
import pandas as pd
import numpy as np
import streamlit as st
from datetime import timedelta


def safe_divide(numerator, denominator, default=0, scale=100):
    """안전한 나눗셈"""
    if denominator == 0 or pd.isna(denominator) or pd.isna(numerator):
        return default
    result = (numerator / denominator) * scale
    if not np.isfinite(result):
        return default
    return round(result, 2)


def format_won(n):
    """원화 포맷팅"""
    if pd.isna(n):
        return "₩0"
    if abs(n) >= 1e8:
        return f"₩{n/1e8:.1f}억"
    if abs(n) >= 1e4:
        return f"₩{n/1e4:,.0f}만"
    return f"₩{n:,.0f}"


def format_number(n):
    """숫자 포맷팅"""
    if pd.isna(n):
        return "0"
    return f"{n:,.0f}"


def format_pct(n):
    """퍼센트 포맷팅"""
    if pd.isna(n) or not np.isfinite(n):
        return "0.0%"
    return f"{n:,.1f}%"


def get_comparison_metrics(df, start_date, end_date):
    """현재 기간 vs 이전 기간 비교 메트릭 계산"""
    if df.empty or 'date' not in df.columns:
        empty_series = pd.Series(dtype=float)
        return empty_series, empty_series, lambda x: 0.0, lambda x, y, z: 0.0

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        empty_series = pd.Series(dtype=float)
        return empty_series, empty_series, lambda x: 0.0, lambda x, y, z: 0.0

    curr_mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
    curr_df = df[curr_mask]

    duration = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration - 1)

    prev_mask = (df['date'].dt.date >= prev_start) & (df['date'].dt.date <= prev_end)
    prev_df = df[prev_mask]

    curr_sums = curr_df[numeric_cols].sum() if not curr_df.empty else pd.Series(0, index=numeric_cols)
    prev_sums = prev_df[numeric_cols].sum() if not prev_df.empty else pd.Series(0, index=numeric_cols)

    def get_delta(col):
        c = curr_sums.get(col, 0)
        p = prev_sums.get(col, 0)
        return safe_divide(c - p, p, default=0, scale=100)

    def get_rate_delta(numerator_col, denominator_col, scale=100):
        cn = curr_sums.get(numerator_col, 0)
        cd = curr_sums.get(denominator_col, 0)
        pn = prev_sums.get(numerator_col, 0)
        pd_val = prev_sums.get(denominator_col, 0)

        curr_rate = safe_divide(cn, cd, default=0, scale=scale)
        prev_rate = safe_divide(pn, pd_val, default=0, scale=scale)

        return round(curr_rate - prev_rate, 1)

    return curr_sums, prev_sums, get_delta, get_rate_delta


def make_weekly(df, date_col='date', group_col=None):
    """일별 데이터를 주별로 집계"""
    if df.empty or date_col not in df.columns:
        return pd.DataFrame()

    t = df.copy()
    try:
        t['week_start'] = t[date_col].dt.to_period('W').apply(lambda x: x.start_time)
    except Exception as e:
        st.warning(f"주 단위 변환 중 오류: {e}")
        return pd.DataFrame()

    nums = [c for c in t.columns if pd.api.types.is_numeric_dtype(t[c]) and c != date_col]
    if not nums:
        return pd.DataFrame()

    if group_col and group_col in t.columns:
        r = t.groupby(['week_start', group_col], dropna=False)[nums].sum().reset_index()
    else:
        r = t.groupby('week_start', dropna=False)[nums].sum().reset_index()

    if r.empty:
        return pd.DataFrame()

    return r.rename(columns={'week_start': 'week'})
