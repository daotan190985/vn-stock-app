# -*- coding: utf-8 -*-
"""
Lớp lấy dữ liệu — bọc vnstock (API mới `vnstock.api`).
Mọi hàm trả về (data, error_message). Nếu lỗi: data=None, error có nội dung.

LƯU Ý: vnstock đôi khi đổi tên cột giữa các version. Code dùng helper
`pick_col` để dò cột theo nhiều tên khả dĩ thay vì hardcode cứng.
"""
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import streamlit as st

DEFAULT_SOURCE = "VCI"  # VCI hỗ trợ BCTC đầy đủ; fallback có thể đổi sang KBS

# ---------- Helpers dò cột linh hoạt ----------

def pick_col(df: pd.DataFrame, candidates, contains=False):
    """Trả về tên cột đầu tiên khớp trong df. Hỗ trợ cột MultiIndex (flatten)."""
    if df is None or df.empty:
        return None
    cols = list(df.columns)
    # flatten nếu MultiIndex
    flat = {}
    for c in cols:
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
        if pd.isna(v):
            return default
        return v
    except Exception:
        return default


# ---------- Lấy dữ liệu (có cache) ----------

@st.cache_data(ttl=3600, show_spinner=False)
def get_company_overview(symbol: str, source: str = DEFAULT_SOURCE):
    try:
        from vnstock.api.company import Company
        c = Company(symbol=symbol.upper(), source=source)
        ov = None
        try:
            ov = c.overview()
        except Exception:
            pass
        info = None
        try:
            info = c.info()
        except Exception:
            pass
        return {"overview": ov, "info": info}, None
    except Exception as e:
        return None, f"Lỗi lấy thông tin DN: {type(e).__name__}: {e}"


@st.cache_data(ttl=3600, show_spinner=False)
def get_ratios(symbol: str, period: str = "quarter", source: str = DEFAULT_SOURCE):
    try:
        from vnstock.api.financial import Finance
        f = Finance(source=source, symbol=symbol.upper(), period=period)
        df = f.ratio(lang="en", dropna=False)
        if df is None or df.empty:
            return None, "Không có dữ liệu chỉ số tài chính."
        return df, None
    except Exception as e:
        return None, f"Lỗi lấy chỉ số: {type(e).__name__}: {e}"


@st.cache_data(ttl=3600, show_spinner=False)
def get_income(symbol: str, period: str = "quarter", source: str = DEFAULT_SOURCE):
    try:
        from vnstock.api.financial import Finance
        f = Finance(source=source, symbol=symbol.upper(), period=period)
        df = f.income_statement(lang="en", dropna=False)
        return (df, None) if df is not None and not df.empty else (None, "Không có BCKQKD.")
    except Exception as e:
        return None, f"Lỗi BCKQKD: {type(e).__name__}: {e}"


@st.cache_data(ttl=3600, show_spinner=False)
def get_balance(symbol: str, period: str = "quarter", source: str = DEFAULT_SOURCE):
    try:
        from vnstock.api.financial import Finance
        f = Finance(source=source, symbol=symbol.upper(), period=period)
        df = f.balance_sheet(lang="en", dropna=False)
        return (df, None) if df is not None and not df.empty else (None, "Không có CĐKT.")
    except Exception as e:
        return None, f"Lỗi CĐKT: {type(e).__name__}: {e}"


@st.cache_data(ttl=3600, show_spinner=False)
def get_cashflow(symbol: str, period: str = "quarter", source: str = DEFAULT_SOURCE):
    try:
        from vnstock.api.financial import Finance
        f = Finance(source=source, symbol=symbol.upper(), period=period)
        df = f.cash_flow(lang="en", dropna=False)
        return (df, None) if df is not None and not df.empty else (None, "Không có LCTT.")
    except Exception as e:
        return None, f"Lỗi LCTT: {type(e).__name__}: {e}"


@st.cache_data(ttl=120, show_spinner=False)
def get_price_board(symbol: str, source: str = "VCI"):
    """Bảng giá realtime: trần/sàn/tham chiếu/khớp lệnh. Trả DataFrame 1 dòng."""
    try:
        from vnstock.api.trading import Trading
        t = Trading(symbol=symbol.upper(), source=source)
        df = t.price_board(symbols_list=[symbol.upper()])
        return (df, None) if df is not None and not df.empty else (None, "Không có bảng giá.")
    except Exception as e:
        return None, f"Lỗi bảng giá: {type(e).__name__}: {e}"


@st.cache_data(ttl=900, show_spinner=False)
def get_price_history(symbol: str, start: str, end: str, interval: str = "1D", source: str = DEFAULT_SOURCE):
    try:
        from vnstock.api.quote import Quote
        q = Quote(symbol=symbol.upper(), source=source, random_agent=True)
        df = q.history(start=start, end=end, interval=interval)
        return (df, None) if df is not None and not df.empty else (None, "Không có dữ liệu giá.")
    except Exception as e:
        return None, f"Lỗi giá: {type(e).__name__}: {e}"
