"""데이터 로딩 및 전처리"""
import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
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
def load_sheet_data(sheet_name: str, recent_rows: int = 10000) -> pd.DataFrame:
    """Google Sheets에서 데이터 로드 (최근 N행만)"""
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(st.secrets["spreadsheet_id"])
        ws = sh.worksheet(sheet_name)

        headers = ws.row_values(1)
        if not headers:
            st.warning(f"시트 '{sheet_name}'에 데이터가 없습니다.")
            return pd.DataFrame()

        total_rows = len(ws.col_values(1))

        if total_rows <= 1:
            st.warning(f"시트 '{sheet_name}'에 데이터가 없습니다.")
            return pd.DataFrame()

        if total_rows <= recent_rows + 1:
            data = ws.get_all_records()
            if not data:
                return pd.DataFrame()
            return pd.DataFrame(data)

        start_row = max(2, total_rows - recent_rows + 1)
        last_col = chr(ord('A') + len(headers) - 1) if len(headers) <= 26 else None

        if last_col:
            range_str = f"A{start_row}:{last_col}{total_rows}"
        else:
            range_str = f"A{start_row}:{total_rows}"

        raw_data = ws.get(range_str)

        if not raw_data:
            st.warning(f"시트 '{sheet_name}'에 데이터가 없습니다.")
            return pd.DataFrame()

        df = pd.DataFrame(raw_data, columns=headers[:len(raw_data[0])] if raw_data else headers)
        return df

    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ 시트 '{sheet_name}'을 찾을 수 없습니다.")
        return pd.DataFrame()
    except gspread.exceptions.APIError as e:
        st.error(f"❌ Google Sheets API 오류: {e}")
        return pd.DataFrame()
    except KeyError as e:
        st.error(f"❌ 설정 오류: {e}. Secrets 설정을 확인하세요.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ 데이터 로드 중 예상치 못한 오류: {e}")
        return pd.DataFrame()


@safe_execution(default_return=pd.DataFrame(), error_message="포인트클릭 데이터 처리 중 오류")
def load_pointclick(df: pd.DataFrame) -> pd.DataFrame:
    """포인트클릭 데이터 전처리"""
    if df.empty:
        return df

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

    numeric_cols = ['unit_price','clicks','conversions','ad_revenue','media_cost','media_rate','margin','margin_rate','cvr']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    df = df[df['date'].notna()].copy()
    return df


@safe_execution(default_return=pd.DataFrame(), error_message="캐시플레이 데이터 처리 중 오류")
def load_cashplay(df: pd.DataFrame) -> pd.DataFrame:
    """캐시플레이 데이터 전처리"""
    if df.empty:
        return df

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

    for c in [x for x in df.columns if x != 'date']:
        df[c] = df[c].replace('-', 0)
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    df = df[df['date'].notna()].copy()
    df['revenue_total'] = df['game_total'] + df['gathering_pointclick'] + df['iaa_total'] + df['offerwall_total']
    df['cost_total'] = df['reward_total']
    df['margin'] = df['revenue_total'] - df['cost_total']
    df['margin_rate'] = df.apply(lambda row: safe_divide(row['margin'], row['revenue_total'], default=0, scale=100), axis=1)
    df['pointclick_revenue'] = df['gathering_pointclick'] + df['offerwall_pointclick']
    df['pointclick_ratio'] = df.apply(lambda row: safe_divide(row['pointclick_revenue'], row['revenue_total'], default=0, scale=100), axis=1)

    return df


@safe_execution(default_return=pd.DataFrame(), error_message="GA4 데이터 처리 중 오류")
def load_ga4(df: pd.DataFrame) -> pd.DataFrame:
    """GA4 데이터 전처리 (공통)"""
    if df.empty:
        return df

    # 날짜 컬럼 처리
    if 'date' in df.columns or '날짜' in df.columns:
        date_col = 'date' if 'date' in df.columns else '날짜'
        df['date'] = pd.to_datetime(df[date_col], errors='coerce')

        if df['date'].isna().all():
            st.error("⚠️ 유효한 날짜 데이터가 없습니다.")
            return pd.DataFrame()

        df = df[df['date'].notna()].copy()

    # 모든 숫자 컬럼 처리
    for col in df.columns:
        if col != 'date' and col != '날짜':
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df
