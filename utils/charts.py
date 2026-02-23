"""차트 및 UI 유틸리티"""
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta, date
from config.constants import CHART_LAYOUT


def week_label(d):
    """주 레이블 생성"""
    try:
        e = d + timedelta(days=6)
        return f"{d.month}/{d.day}~{e.month}/{e.day}"
    except:
        return str(d)


def fmt_axis_won(val):
    """축 레이블용 원화 포맷"""
    if pd.isna(val):
        return "0"
    av = abs(val)
    sign = "-" if val < 0 else ""
    if av >= 1e8:
        return f"{sign}{val/1e8:.1f}억"
    if av >= 1e4:
        return f"{sign}{val/1e4:,.0f}만"
    return f"{sign}{val:,.0f}"


def set_y_korean_ticks(fig, values):
    """Y축에 한국어 단위 눈금 설정"""
    if not values or len(values) == 0:
        return

    values = [v for v in values if pd.notna(v) and np.isfinite(v)]
    if not values:
        return

    vmax = max(abs(v) for v in values)
    if vmax == 0:
        return

    nice = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
    unit = 1e8 if vmax >= 1e8 else (1e4 if vmax >= 1e4 else 1)
    step_units = (vmax / 5) / unit
    chosen = 1
    for n in nice:
        if n >= step_units:
            chosen = n
            break
    step = chosen * unit
    mn = min(values)
    tick_vals, tick_texts = [], []
    v = 0
    while v <= vmax * 1.15:
        tick_vals.append(v)
        tick_texts.append(fmt_axis_won(v))
        if mn < 0:
            tick_vals.append(-v)
            tick_texts.append(fmt_axis_won(-v))
        v += step
        if v > 1e12:
            break

    try:
        fig.update_yaxes(tickvals=tick_vals, ticktext=tick_texts, selector=dict(overlaying=None))
    except:
        pass


def apply_layout(fig, extra=None):
    """차트에 레이아웃 적용"""
    layout = {**CHART_LAYOUT}
    if extra:
        layout.update(extra)
    fig.update_layout(**layout)
    return fig


def quick_date_picker(data_min, data_max, prefix, default_mode="이번달"):
    """빠른 날짜 선택기"""
    today = date.today()
    yesterday = today - timedelta(days=1)

    prev_month_first = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    presets = {
        "오늘": (today, today),
        "어제": (yesterday, yesterday),
        "이번주": (today - timedelta(days=today.weekday()), today),
        "전주": (today - timedelta(days=today.weekday() + 7), today - timedelta(days=today.weekday() + 1)),
        "이번달": (today.replace(day=1), today),
        "전월": (prev_month_first, today.replace(day=1) - timedelta(days=1)),
        "이전달1일": (prev_month_first, today),
        "올해": (date(today.year, 1, 1), today),
    }

    def clamp(d):
        try:
            return max(data_min, min(d, data_max))
        except:
            return d

    key_from = f"{prefix}_di_from"
    key_to = f"{prefix}_di_to"
    key_seg = f"{prefix}_seg"

    def safe_date(val, fallback):
        """튜플/리스트/None 등 오염된 session state 값을 단일 date로 정규화"""
        if val is None:
            return fallback
        if isinstance(val, (list, tuple)):
            return val[0] if val else fallback
        if isinstance(val, date):
            return val
        return fallback

    ds_default, de_default = presets.get(default_mode, (today, today))

    raw_from = st.session_state.get(key_from)
    raw_to = st.session_state.get(key_to)

    if raw_from is None:
        st.session_state[key_from] = clamp(ds_default)
        st.session_state[key_to] = clamp(de_default)
    else:
        st.session_state[key_from] = clamp(safe_date(raw_from, ds_default))
        st.session_state[key_to] = clamp(safe_date(raw_to, de_default))

    current_from = st.session_state[key_from]
    current_to = st.session_state[key_to]
    current_preset = None
    for label, (ps, pe) in presets.items():
        if clamp(ps) == current_from and clamp(pe) == current_to:
            current_preset = label
            break

    selected = st.segmented_control(
        label="기간 선택",
        options=list(presets.keys()),
        default=current_preset,
        key=key_seg,
        label_visibility="collapsed",
    )

    if selected and selected in presets:
        ps, pe = presets[selected]
        new_from = clamp(ps)
        new_to = clamp(pe)
        if new_from != current_from or new_to != current_to:
            st.session_state[key_from] = new_from
            st.session_state[key_to] = new_to

    # key= 를 쓸 때 value= 를 함께 넘기면 충돌하므로,
    # 위에서 session state를 단일 date로 정규화한 후 key= 만 사용.
    dc1, dc2, _ = st.columns([1, 1, 8], gap="small")
    with dc1:
        d_from = st.date_input("시작일", min_value=data_min, max_value=data_max, key=key_from)
    with dc2:
        d_to = st.date_input("종료일", min_value=data_min, max_value=data_max, key=key_to)

    return d_from, d_to
