# -*- coding: utf-8 -*-
"""
Bộ quét thị trường (Screener).
Quét cả vũ trụ cổ phiếu, chấm điểm cơ bản + kỹ thuật, gắn trạng thái điểm vào,
cộng "gió ngành" (sector tailwind) theo giai đoạn vĩ mô đang chọn.

Kết quả: bảng xếp hạng để analyst mở app là có ngay danh sách theo dõi.
"""
from datetime import datetime, timedelta
import pandas as pd

import data as D
import analyzer as A
import market as MK
import sectors as S

# map mã -> ngành (đảo từ SECTOR_TICKERS)
_TICKER_SECTOR = {}
for _sec, _lst in S.SECTOR_TICKERS.items():
    for _t in _lst:
        _TICKER_SECTOR[_t] = _sec


def sector_of(symbol):
    return _TICKER_SECTOR.get(symbol.upper(), "Khác")


STATUS_LABEL = {
    "VAO": "🟢 ĐIỂM VÀO",
    "CHO": "🟡 CHỜ ĐIỂM VÀO",
    "THEODOI": "🔵 THEO DÕI",
    "TRANH": "🔴 TRÁNH",
}
STATUS_ORDER = {"VAO": 0, "CHO": 1, "THEODOI": 2, "TRANH": 3}


def scan_one(sym, period, source, favored_sectors=None):
    """Quét 1 mã: cơ bản + kỹ thuật + điểm vào. Trả dict gọn cho bảng."""
    favored_sectors = favored_sectors or set()
    row = {"Mã": sym, "Ngành": sector_of(sym), "status": "THEODOI",
           "Trạng thái": "", "Điểm CB": None, "Setup": "", "RSI": None,
           "Xu hướng": "", "Giá": None, "P/E": None, "ROE%": None,
           "Cảnh báo": 0, "Gió ngành": "", "_err": []}
    try:
        ratio, e1 = D.get_ratios(sym, period, source)
        income, _ = D.get_income(sym, period, source)
        cashf, _ = D.get_cashflow(sym, period, source)
        cur, _ = A.extract_metrics(ratio)
        growth = A.compute_growth(income)
        cf = A.analyze_cashflow(cashf)
        warns = A.detect_warnings(cur, growth, cf)
        sc = A.score_stock(cur, growth, cf)

        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        hist, _ = D.get_price_history(sym, start, end, "1D", source)
        setup = MK.entry_setup(hist)

        row["Điểm CB"] = sc["total"]
        row["P/E"] = round(cur["pe"], 1) if cur.get("pe") else None
        row["ROE%"] = round(cur["roe"], 1) if cur.get("roe") else None
        row["RSI"] = setup.get("rsi")
        row["Xu hướng"] = setup.get("trend") or ""
        row["Giá"] = setup.get("price")
        row["Cảnh báo"] = len(warns)
        row["status"] = setup.get("status", "THEODOI")
        row["Setup"] = setup["reasons"][0] if setup.get("reasons") else ""

        # Gió ngành: nếu ngành nằm trong nhóm hưởng lợi giai đoạn đang chọn
        if row["Ngành"] in favored_sectors:
            row["Gió ngành"] = "✅ thuận"
        row["Trạng thái"] = STATUS_LABEL.get(row["status"], "")
    except Exception as ex:
        row["_err"].append(f"{type(ex).__name__}: {ex}")
    return row


def rank_key(row):
    """Sắp xếp: trạng thái vào trước, rồi điểm cơ bản cao, gió ngành thuận."""
    st = STATUS_ORDER.get(row.get("status"), 9)
    cb = row.get("Điểm CB") or 0
    wind = 1 if row.get("Gió ngành") else 0
    return (st, -wind, -cb)


def run_screen(symbols, period, source, favored_sectors=None, progress_cb=None):
    rows = []
    n = len(symbols)
    for i, sym in enumerate(symbols):
        rows.append(scan_one(sym, period, source, favored_sectors))
        if progress_cb:
            progress_cb((i + 1) / n, sym)
    rows.sort(key=rank_key)
    return rows
