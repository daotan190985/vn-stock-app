# -*- coding: utf-8 -*-
"""
Lớp lấy dữ liệu — VNDirect là nguồn CHÍNH (đã kiểm chứng chạy từ cloud).
vnstock chỉ là dự phòng (hay bị chặn IP trên cloud).
Mọi hàm trả (data, error).
"""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd
import streamlit as st
import vndirect as VND

DEFAULT_SOURCE = "VCI"  # chỉ dùng cho vnstock dự phòng


def pick_col(df, candidates, contains=False):
    if df is None or df.empty:
        return None
    flat = {}
    for c in df.columns:
        key = " ".join([str(x) for x in c]) if isinstance(c, tuple) else str(c)
        flat[key.lower().strip()] = c
    for cand in candidates:
        cl = cand.lower().strip()
        if contains:
            for k, orig in flat.items():
                if cl in k:
                    return orig
        else:
            if cl in flat:
                return flat[cl]
    return None


def safe_get(row, col, default=None):
    try:
        if col is None:
            return default
        v = row[col]
        return default if pd.isna(v) else v
    except Exception:
        return default


@st.cache_data(ttl=900, show_spinner=False)
def get_price_history(symbol, start, end, interval="1D", source=DEFAULT_SOURCE):
    # 1) VNDirect dchart (chính)
    df = VND.vnd_history(symbol, start, end)
    if df is not None and not df.empty:
        return df, None
    # 2) vnstock dự phòng
    try:
        from vnstock.api.quote import Quote
        q = Quote(symbol=symbol.upper(), source=source, random_agent=True)
        df = q.history(start=start, end=end, interval=interval)
        if df is not None and not df.empty:
            return df, None
    except Exception:
        pass
    return None, "Không lấy được giá (VNDirect + vnstock)."


@st.cache_data(ttl=3600, show_spinner=False)
def get_ratios(symbol, period="quarter", source=DEFAULT_SOURCE):
    # 1) VNDirect finfo (best-effort)
    df = VND.vnd_ratios_df(symbol)
    if df is not None and not df.empty:
        return df, None
    # 2) vnstock dự phòng
    try:
        from vnstock.api.financial import Finance
        f = Finance(source=source, symbol=symbol.upper(), period=period)
        df = f.ratio(lang="en", dropna=False)
        if df is not None and not df.empty:
            return df, None
    except Exception:
        pass
    return None, "Chỉ số tài chính tạm không có (finfo 503 / vnstock chặn)."


@st.cache_data(ttl=3600, show_spinner=False)
def get_income(symbol, period="quarter", source=DEFAULT_SOURCE):
    try:
        from vnstock.api.financial import Finance
        f = Finance(source=source, symbol=symbol.upper(), period=period)
        df = f.income_statement(lang="en", dropna=False)
        return (df, None) if df is not None and not df.empty else (None, "Không có BCKQKD.")
    except Exception as e:
        return None, f"BCKQKD tạm không có: {type(e).__name__}"


@st.cache_data(ttl=3600, show_spinner=False)
def get_cashflow(symbol, period="quarter", source=DEFAULT_SOURCE):
    try:
        from vnstock.api.financial import Finance
        f = Finance(source=source, symbol=symbol.upper(), period=period)
        df = f.cash_flow(lang="en", dropna=False)
        return (df, None) if df is not None and not df.empty else (None, "Không có LCTT.")
    except Exception as e:
        return None, f"LCTT tạm không có: {type(e).__name__}"


@st.cache_data(ttl=120, show_spinner=False)
def get_price_board(symbol, source=DEFAULT_SOURCE):
    """Bảng giá: thử vnstock; nếu không có sẽ để app tự suy trần/sàn từ lịch sử giá."""
    try:
        from vnstock.api.trading import Trading
        t = Trading(symbol=symbol.upper(), source=source)
        df = t.price_board(symbols_list=[symbol.upper()])
        return (df, None) if df is not None and not df.empty else (None, "Không có bảng giá.")
    except Exception as e:
        return None, f"Bảng giá tạm không có: {type(e).__name__}"
