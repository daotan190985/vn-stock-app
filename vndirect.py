# -*- coding: utf-8 -*-
"""
Nguồn dữ liệu CHÍNH: VNDirect (API công khai, đã kiểm chứng chạy từ cloud).

- Giá OHLCV: dchart-api  -> ỔN ĐỊNH, là trụ cột.
- Chỉ số/BCTC: finfo-api  -> best-effort (hay 503), có thử lại; thiếu thì bỏ qua.
- Trần/sàn/tham chiếu: SUY TỪ giá (đóng cửa phiên trước) -> không phụ thuộc finfo.

Mọi hàm an toàn: lỗi -> None, không làm vỡ app.
"""
import warnings; warnings.filterwarnings("ignore")
from datetime import datetime
import time as _time
import pandas as pd
import requests

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://dstock.vndirect.com.vn/",
}
_TIMEOUT = 12


def _get_json(url, tries=3, backoff=1.2):
    """GET có thử lại khi 503/lỗi tạm. Trả dict JSON hoặc None."""
    for i in range(tries):
        try:
            r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            if r.status_code == 200 and len(r.text) > 20:
                return r.json()
            if r.status_code in (429, 502, 503, 504):
                _time.sleep(backoff * (i + 1)); continue
            return None
        except Exception:
            _time.sleep(backoff * (i + 1))
    return None


# ---------------- GIÁ (trụ cột) ----------------
def vnd_history(symbol, start, end):
    """Giá ngày OHLCV từ dchart. start/end 'YYYY-MM-DD'.
    Trả DataFrame: time, open, high, low, close, volume."""
    try:
        ts_from = int(datetime.strptime(start, "%Y-%m-%d").timestamp())
        ts_to = int(datetime.strptime(end, "%Y-%m-%d").timestamp())
        url = ("https://dchart-api.vndirect.com.vn/dchart/history"
               f"?resolution=D&symbol={symbol.upper()}&from={ts_from}&to={ts_to}")
        j = _get_json(url)
        if not j or j.get("s") != "ok" or not j.get("t"):
            return None
        df = pd.DataFrame({
            "time": pd.to_datetime(j["t"], unit="s"),
            "open": j["o"], "high": j["h"], "low": j["l"],
            "close": j["c"], "volume": j.get("v", [0] * len(j["t"])),
        })
        return df
    except Exception:
        return None


# ---------------- CHỈ SỐ (best-effort) ----------------
_RATIO_MAP = {
    "ROE": "ROE (%)", "ROA": "ROA (%)",
    "PRICE_TO_EARNINGS": "P/E", "PRICE_TO_BOOK": "P/B",
    "NET_PROFIT_MARGIN": "Net Profit Margin (%)",
    "GROSS_PROFIT_MARGIN": "Gross Profit Margin (%)",
    "DEBT_ON_EQUITY": "Debt/Equity", "CURRENT_RATIO": "Current Ratio",
}

def vnd_ratios_df(symbol):
    """Chỉ số mới nhất từ finfo (best-effort). Trả 1 dòng DataFrame kiểu vnstock,
    hoặc None nếu finfo không phản hồi (503...)."""
    for url in (
        f"https://finfo-api.vndirect.com.vn/v4/ratios?q=code:{symbol.upper()}~reportType:QUARTER&sort=reportDate&size=40",
        f"https://finfo-api.vndirect.com.vn/v4/ratios/latest?order=reportDate&where=code:{symbol.upper()}~reportType:QUARTER&size=40",
    ):
        j = _get_json(url, tries=2)
        data = (j or {}).get("data") if j else None
        if not data:
            continue
        latest = {}
        for item in data:
            code = item.get("ratioCode") or item.get("itemCode")
            val = item.get("value")
            if code in _RATIO_MAP and code not in latest and val is not None:
                latest[code] = val
        if not latest:
            continue
        row = {}
        for code, val in latest.items():
            col = _RATIO_MAP[code]
            if col.endswith("(%)") and val is not None and abs(val) < 5:
                val = val * 100  # tỉ lệ -> %
            row[col] = val
        row["yearReport"] = datetime.now().year
        row["lengthReport"] = 1
        return pd.DataFrame([row])
    return None


# ---------------- TRẦN/SÀN/THAM CHIẾU (suy từ giá) ----------------
def ref_from_history(hist_df):
    """Tham chiếu = giá đóng cửa phiên GẦN NHẤT TRƯỚC phiên cuối.
    Không cần finfo. Trả float hoặc None. (giá dchart đơn vị nghìn đồng)"""
    try:
        if hist_df is None or hist_df.empty or "close" not in hist_df.columns:
            return None
        closes = pd.to_numeric(hist_df["close"], errors="coerce").dropna()
        if len(closes) >= 2:
            return float(closes.iloc[-2])
        return float(closes.iloc[-1])
    except Exception:
        return None


def last_price(symbol):
    """Giá đóng cửa gần nhất (nghìn đồng) từ dchart. None nếu lỗi."""
    from datetime import datetime, timedelta
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
        df = vnd_history(symbol, start, end)
        if df is None or df.empty:
            return None
        import pandas as pd
        c = pd.to_numeric(df["close"], errors="coerce").dropna()
        return round(float(c.iloc[-1]), 2) if len(c) else None
    except Exception:
        return None
