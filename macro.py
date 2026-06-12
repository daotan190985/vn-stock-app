# -*- coding: utf-8 -*-
"""
Bối cảnh vĩ mô: VN-Index lấy qua VNDirect dchart (mã VNINDEX) -> chạy được trên cloud.
"""
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import sectors as S
import vndirect as VND


@st.cache_data(ttl=900, show_spinner=False)
def vnindex_trend(source="VCI"):
    out = {"last": None, "ma50": None, "ma200": None, "trend": None, "chg_1m": None, "err": None}
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        df = VND.vnd_history("VNINDEX", start, end)
        if df is None or df.empty:
            out["err"] = "Không lấy được VN-Index."; return out
        s = pd.to_numeric(df["close"], errors="coerce").dropna()
        out["last"] = round(float(s.iloc[-1]), 1)
        if len(s) >= 50:  out["ma50"]  = round(float(s.rolling(50).mean().iloc[-1]), 1)
        if len(s) >= 200: out["ma200"] = round(float(s.rolling(200).mean().iloc[-1]), 1)
        if len(s) > 21:   out["chg_1m"] = round((s.iloc[-1]-s.iloc[-21])/s.iloc[-21]*100, 1)
        if out["last"] and out["ma50"] and out["ma200"]:
            if out["last"] > out["ma50"] > out["ma200"]: out["trend"] = "Tăng (uptrend)"
            elif out["last"] < out["ma50"] < out["ma200"]: out["trend"] = "Giảm (downtrend)"
            else: out["trend"] = "Đi ngang / phân hóa"
    except Exception as e:
        out["err"] = f"{type(e).__name__}: {e}"
    return out


def favored_sectors_for_phase(phase_key):
    info = S.ECONOMIC_PHASES.get(phase_key, {})
    favored = set()
    name_map = {
        "ngân hàng":"Ngân hàng","bất động sản":"Bất động sản","chứng khoán":"Chứng khoán",
        "thép":"Thép & Vật liệu","vật liệu":"Thép & Vật liệu","bán lẻ":"Bán lẻ",
        "công nghệ":"Công nghệ","chuyển đổi số":"Công nghệ","bán dẫn":"Công nghệ",
        "dầu khí":"Dầu khí","tài nguyên":"Dầu khí","điện":"Điện & Tiện ích",
        "tiện ích":"Điện & Tiện ích","năng lượng":"Điện & Tiện ích",
        "hàng không":"Hàng không & Du lịch","du lịch":"Hàng không & Du lịch",
        "vận tải biển":"Vận tải biển & Logistics","logistics":"Vận tải biển & Logistics",
        "dược":"Dược phẩm","tiêu dùng":"Hàng tiêu dùng","khu công nghiệp":"Khu công nghiệp",
        "xây dựng":"Xây dựng","đầu tư công":"Xây dựng","hạ tầng":"Xây dựng",
    }
    for name, _ in info.get("huong_loi", []):
        low = name.lower()
        for kw, sec in name_map.items():
            if kw in low: favored.add(sec)
    return favored
