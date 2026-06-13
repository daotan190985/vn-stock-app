# -*- coding: utf-8 -*-
"""
Lấy cổ tức từ Vietstock (chạy trên MÁY VN — IP người thật).
Dùng cách đã kiểm chứng chạy được: đọc bảng /co-tuc.htm bằng pandas.read_html.
Chỉ dùng trong cap_nhat_co_ban.py (máy anh), KHÔNG gọi từ cloud.
"""
import warnings; warnings.filterwarnings("ignore")
import re
from io import StringIO
import requests
import pandas as pd

_H = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://finance.vietstock.vn/",
}


def get_dividends_raw(symbol):
    """Trả DataFrame cổ tức (cột 0=ngày, cột 1=nội dung) hoặc None."""
    url = f"https://finance.vietstock.vn/{symbol.upper()}/co-tuc.htm"
    try:
        r = requests.get(url, headers=_H, timeout=15)
        r.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", class_=lambda x: x and "table" in x)
        if not table:
            return None
        df = pd.read_html(StringIO(str(table)))[0]
        return df if not df.empty else None
    except Exception:
        return None


def latest_dividend_info(symbol):
    """Rút gọn cổ tức cho 1 mã -> dict:
    {last_event, last_date, has_upcoming, lines[]} hoặc {} nếu không có.
    Phân loại sơ bộ: tỷ lệ %, tiền/cổ phiếu nếu bắt được."""
    df = get_dividends_raw(symbol)
    if df is None or df.empty:
        return {}
    rows = []
    for _, r in df.head(8).iterrows():
        date = str(r.iloc[0]).strip()
        content = str(r.iloc[1]).strip() if len(r) > 1 else ""
        if not content or content == "nan":
            continue
        # bắt tỷ lệ % hoặc đồng
        pct = re.search(r'(\d+(?:[.,]\d+)?)\s*%', content)
        rows.append({"ngay": date, "noi_dung": content[:200],
                     "ty_le": pct.group(0) if pct else ""})
    if not rows:
        return {}
    return {"last_date": rows[0]["ngay"], "last_event": rows[0]["noi_dung"],
            "last_ratio": rows[0]["ty_le"], "lines": rows[:5]}
