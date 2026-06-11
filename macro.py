# -*- coding: utf-8 -*-
"""
Bối cảnh Kinh tế Vĩ mô.

Phần định lượng LẤY THẬT được: xu hướng VN-Index (qua chỉ số).
Phần định tính (lãi suất, lạm phát, chính sách): analyst tự đặt qua input,
app dùng để xác định "giai đoạn vĩ mô" -> tô đậm nhóm ngành hưởng lợi (gió ngành).

Mục tiêu: nối vĩ mô -> sector rotation -> screener, để khuyến nghị có bối cảnh.
"""
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import data as D
import sectors as S


@st.cache_data(ttl=900, show_spinner=False)
def vnindex_trend(source="VCI"):
    """Lấy VN-Index và đánh giá xu hướng qua MA50/MA200."""
    out = {"last": None, "ma50": None, "ma200": None, "trend": None, "chg_1m": None, "err": None}
    try:
        from vnstock.api.quote import Quote
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        # VNINDEX là mã chỉ số
        q = Quote(symbol="VNINDEX", source=source, random_agent=True)
        df = q.history(start=start, end=end, interval="1D")
        if df is None or df.empty:
            out["err"] = "Không lấy được VN-Index."; return out
        from data import pick_col
        c = pick_col(df, ["close"], contains=True)
        s = pd.to_numeric(df[c], errors="coerce")
        out["last"] = round(float(s.iloc[-1]), 1)
        out["ma50"] = round(float(s.rolling(50).mean().iloc[-1]), 1)
        out["ma200"] = round(float(s.rolling(200).mean().iloc[-1]), 1)
        if len(s) > 21:
            out["chg_1m"] = round((s.iloc[-1] - s.iloc[-21]) / s.iloc[-21] * 100, 1)
        if out["last"] and out["ma50"] and out["ma200"]:
            if out["last"] > out["ma50"] > out["ma200"]:
                out["trend"] = "Tăng (uptrend)"
            elif out["last"] < out["ma50"] < out["ma200"]:
                out["trend"] = "Giảm (downtrend)"
            else:
                out["trend"] = "Đi ngang / phân hóa"
    except Exception as e:
        out["err"] = f"{type(e).__name__}: {e}"
    return out


def favored_sectors_for_phase(phase_key):
    """Trả về tập tên ngành (khớp SECTOR_TICKERS) hưởng lợi ở giai đoạn đã chọn."""
    info = S.ECONOMIC_PHASES.get(phase_key, {})
    favored = set()
    # map mô tả ngành trong ECONOMIC_PHASES -> tên ngành trong SECTOR_TICKERS
    name_map = {
        "ngân hàng": "Ngân hàng", "bất động sản": "Bất động sản", "chứng khoán": "Chứng khoán",
        "thép": "Thép & Vật liệu", "vật liệu": "Thép & Vật liệu", "bán lẻ": "Bán lẻ",
        "công nghệ": "Công nghệ", "chuyển đổi số": "Công nghệ", "bán dẫn": "Công nghệ",
        "dầu khí": "Dầu khí", "tài nguyên": "Dầu khí", "điện": "Điện & Tiện ích",
        "tiện ích": "Điện & Tiện ích", "năng lượng": "Điện & Tiện ích",
        "hàng không": "Hàng không & Du lịch", "du lịch": "Hàng không & Du lịch",
        "vận tải biển": "Vận tải biển & Logistics", "logistics": "Vận tải biển & Logistics",
        "dược": "Dược phẩm", "tiêu dùng": "Hàng tiêu dùng", "khu công nghiệp": "Khu công nghiệp",
        "xây dựng": "Xây dựng", "đầu tư công": "Xây dựng", "hạ tầng": "Xây dựng",
    }
    for name, _why in info.get("huong_loi", []):
        low = name.lower()
        for kw, sec in name_map.items():
            if kw in low:
                favored.add(sec)
    return favored
