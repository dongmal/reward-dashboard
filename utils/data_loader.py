"""데이터 로딩 및 전처리 (Supabase 기반)"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from functools import wraps
from .metrics import safe_divide


def safe_execution(default_return=None, error_message="오류가 발생했습니다"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                st.error(f"{error_message}: {str(e)}")
                if default_return is not None:
                    return default_return
                return pd.DataFrame() if 'load' in func.__name__ else None
        return wrapper
    return decorator


@st.cache_data(ttl=3600, show_spinner=False)
def load_supabase_data(table_name: str, recent_days: int = None) -> pd.DataFrame:
    """Supabase에서 데이터 로드

    Args:
        table_name: Supabase 테이블명
        recent_days: 최근 N일만 조회 (None이면 전체)
    """
    try:
        from utils.supabase_client import get_supabase
        client = get_supabase()

        # Supabase REST API 기본 제한(1000행)을 우회하기 위해 페이지네이션 적용
        CHUNK = 1000
        all_data = []
        offset = 0

        while True:
            q = client.table(table_name).select("*")
            if recent_days is not None:
                cutoff = (date.today() - timedelta(days=recent_days)).isoformat()
                q = q.gte("date", cutoff)
            response = q.order("date").range(offset, offset + CHUNK - 1).execute()

            if not response.data:
                break
            all_data.extend(response.data)
            if len(response.data) < CHUNK:
                break
            offset += CHUNK

        if not all_data:
            return pd.DataFrame()

        return pd.DataFrame(all_data)

    except KeyError as e:
        st.error(f"❌ 설정 오류: {e} 키가 Secrets에 없습니다. SUPABASE_URL / SUPABASE_KEY를 확인하세요.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Supabase 데이터 로드 중 오류 [{table_name}]: {e}")
        return pd.DataFrame()


@safe_execution(default_return=pd.DataFrame(), error_message="포인트클릭 데이터 처리 중 오류")
def load_pointclick(df: pd.DataFrame) -> pd.DataFrame:
    """포인트클릭 데이터 전처리"""
    if df.empty:
        return df

    # Supabase는 이미 영어 컬럼명으로 저장됨 (하위 호환: 한글 컬럼명도 처리)
    col_map = {
        '일자': 'date', '광고구분': 'ad_category', '매체타입': 'media_type',
        '퍼블리셔타입': 'publisher_type', '광고명': 'ad_name', '매체명': 'media_name',
        'CD': 'cd', '광고주명': 'advertiser', 'OS': 'os', '광고타입': 'ad_type',
        '광고단가': 'unit_price', '클릭수': 'clicks', '전환수': 'conversions',
        '광고비': 'ad_revenue', '매체수익금': 'media_cost', '매체정산비율': 'media_rate',
        '마진금액': 'margin', '마진율': 'margin_rate', 'CVR': 'cvr',
        '주차': 'week', '월별': 'month'
    }
    df = df.rename(columns=col_map)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    if df['date'].isna().all():
        st.error("⚠️ 유효한 날짜 데이터가 없습니다.")
        return pd.DataFrame()

    numeric_cols = ['unit_price', 'clicks', 'conversions', 'ad_revenue', 'media_cost',
                    'media_rate', 'margin', 'margin_rate', 'cvr']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    df = df[df['date'].notna()].copy()

    # id 컬럼 제거 (Supabase 자동생성)
    df = df.drop(columns=['id'], errors='ignore')

    return df


@safe_execution(default_return=pd.DataFrame(), error_message="캐시플레이 데이터 처리 중 오류")
def load_cashplay(df: pd.DataFrame) -> pd.DataFrame:
    """캐시플레이 데이터 전처리"""
    if df.empty:
        return df

    # Supabase는 이미 영어 컬럼명으로 저장됨 (하위 호환: 한글 컬럼명도 처리)
    col_map = {
        '날짜': 'date',
        '리워드(원)_유상': 'reward_paid', '리워드(원)_무상': 'reward_free', '리워드(원)_합계': 'reward_total',
        '게임(원)_직거래': 'game_direct', '게임(원)_DSP': 'game_dsp', '게임(원)_RS': 'game_rs',
        '게임(원)_인수': 'game_acquisition', '게임(원)_합계': 'game_total',
        '게더링(원)_포인트클릭': 'gathering_pointclick',
        'IAA(원)_레벨플레이': 'iaa_levelplay', 'IAA(원)_애드웨일': 'iaa_adwhale',
        'IAA(원)_허블': 'iaa_hubble', 'IAA(원)_합계': 'iaa_total',
        '오퍼월(원)_애드팝콘': 'offerwall_adpopcorn', '오퍼월(원)_포인트클릭': 'offerwall_pointclick',
        '오퍼월(원)_아이브': 'offerwall_ive', '오퍼월(원)_애드포러스': 'offerwall_adforus',
        '오퍼월(원)_애디슨': 'offerwall_addison', '오퍼월(원)_애드조': 'offerwall_adjo',
        '오퍼월(원)_합계': 'offerwall_total'
    }
    df = df.rename(columns=col_map)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    if df['date'].isna().all():
        st.error("⚠️ 유효한 날짜 데이터가 없습니다.")
        return pd.DataFrame()

    numeric_cols = [c for c in df.columns if c != 'date']
    for c in numeric_cols:
        df[c] = df[c].replace('-', 0) if df[c].dtype == object else df[c]
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    df = df[df['date'].notna()].copy()
    df['revenue_total'] = df['game_total'] + df['gathering_pointclick'] + df['iaa_total'] + df['offerwall_total']
    df['cost_total'] = df['reward_total']
    df['margin'] = df['revenue_total'] - df['cost_total']
    df['margin_rate'] = df.apply(lambda row: safe_divide(row['margin'], row['revenue_total'], default=0, scale=100), axis=1)
    df['pointclick_revenue'] = df['gathering_pointclick'] + df['offerwall_pointclick']
    df['pointclick_ratio'] = df.apply(lambda row: safe_divide(row['pointclick_revenue'], row['revenue_total'], default=0, scale=100), axis=1)

    return df


@safe_execution(default_return=pd.DataFrame(), error_message="매체 마스터 데이터 처리 중 오류")
def load_media_master(df: pd.DataFrame) -> pd.DataFrame:
    """매체 마스터 데이터 전처리"""
    if df.empty:
        return df

    col_map = {
        '매체키': 'media_key',
        '매체명': 'media_name'
    }
    df = df.rename(columns=col_map)

    if 'media_key' not in df.columns or 'media_name' not in df.columns:
        st.error("⚠️ 매체 마스터에 필수 컬럼(media_key, media_name)이 없습니다.")
        return pd.DataFrame()

    df = df[['media_key', 'media_name']].drop_duplicates(subset=['media_key'])
    return df


@safe_execution(default_return=pd.DataFrame(), error_message="GA4 데이터 처리 중 오류")
def load_ga4(df: pd.DataFrame) -> pd.DataFrame:
    """GA4 데이터 전처리 (공통)

    Supabase(PostgreSQL)는 quoted 컬럼명도 소문자로 내려줄 수 있으므로
    camelCase 컬럼명을 복원한다.
    """
    if df.empty:
        return df

    # PostgreSQL 소문자 컬럼 → GA4 API 원본 camelCase 복원
    camel_restore = {
        'eventname': 'eventName',
        'pagetitle': 'pageTitle',
        'pagepath': 'pagePath',
        'eventcount': 'eventCount',
        'screenpageviews': 'screenPageViews',
        'averagesessionduration': 'averageSessionDuration',
        'engagementrate': 'engagementRate',
        'userengagementduration': 'userEngagementDuration',
        'activeusers': 'activeUsers',
        'active7dayusers': 'active7DayUsers',
        'active28dayusers': 'active28DayUsers',
        'newusers': 'newUsers',
    }
    df = df.rename(columns={k: v for k, v in camel_restore.items() if k in df.columns})

    # 날짜 컬럼 처리
    if 'date' in df.columns or '날짜' in df.columns:
        date_col = 'date' if 'date' in df.columns else '날짜'
        df['date'] = pd.to_datetime(df[date_col], errors='coerce')

        if df['date'].isna().all():
            st.error("⚠️ 유효한 날짜 데이터가 없습니다.")
            return pd.DataFrame()

        df = df[df['date'].notna()].copy()

    # 숫자 컬럼 변환 (문자열로 저장된 경우 대비)
    skip_cols = {'date', '날짜', 'id', 'eventName', 'pageTitle', 'pagePath',
                 'page_name', 'page_type', 'media_key', 'media_name',
                 'page', 'button_id'}
    for col in df.columns:
        if col not in skip_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # id 컬럼 제거 (Supabase 자동생성)
    df = df.drop(columns=['id'], errors='ignore')

    return df
