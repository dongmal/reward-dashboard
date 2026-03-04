"""Supabase 클라이언트 헬퍼"""
import os
import streamlit as st
from supabase import create_client, Client


def get_supabase() -> Client:
    """Supabase 클라이언트 생성 (Streamlit secrets 환경)"""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def get_supabase_from_env() -> Client:
    """Supabase 클라이언트 생성 (환경변수 환경 - GitHub Actions 등)"""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)
