# -*- coding: utf-8 -*-
"""
Bộ quét thị trường (Screener) — bản TỐI ƯU TỐC ĐỘ.

Cải tiến chính:
- Quét SONG SONG nhiều mã cùng lúc (ThreadPoolExecutor) thay vì tuần tự.
- Mỗi mã chỉ gọi 2 nguồn cần thiết cho bảng: ratio (chỉ số) + history (giá).
  Income/cashflow (tăng trưởng, dòng tiền) để dành cho tab Phân tích chi tiết.
- random_agent=True để giảm bị chặn IP.
- Lỗi 1 mã không làm hỏng cả lượt quét.
"""
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import analyzer as A
import market as MK
import sectors as S

_TICKER_SECTOR = {}
for _sec, _lst in S.SECTOR_TICKERS.items():
    for _t in _lst:
        _TICKER_SECTOR[_t] = _sec

def sector_of(symbol):
    return _TICKER_SECTOR.get(symbol.upper(), "Khác")

STATUS_LABEL = {
    "VAO": "🟢 ĐIỂM VÀO", "CHO": "🟡 CHỜ ĐIỂM VÀO",
    "THEODOI": "🔵 THEO DÕI", "TRANH": "🔴 TRÁNH",
}
STATUS_ORDER = {"VAO": 0, "CHO": 1, "THEODOI": 2, "TRANH": 3}


def _fetch_raw(sym, period, source):
    """Gọi vnstock trực tiếp (không qua st.cache để an toàn khi đa luồng)."""
    out = {"ratio": None, "hist": None, "err": None}
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=320)).strftime("%Y-%m-%d")
    try:
        from vnstock.api.financial import Finance
        f = Finance(source=source, symbol=sym.upper(), period=period)
        out["ratio"] = f.ratio(lang="en", dropna=False)
    except Exception as e:
        out["err"] = f"ratio: {type(e).__name__}"
    try:
        from vnstock.api.quote import Quote
        q = Quote(symbol=sym.upper(), source=source, random_agent=True)
        out["hist"] = q.history(start=start, end=end, interval="1D")
    except Exception as e:
        out["err"] = (out["err"] or "") + f" | hist: {type(e).__name__}"
    return out


def _process(sym, raw, favored_sectors):
    """Tính toán nhẹ (CPU) từ dữ liệu thô — không gọi mạng."""
    favored_sectors = favored_sectors or set()
    row = {"Mã": sym, "Ngành": sector_of(sym), "status": "THEODOI",
           "Trạng thái": "", "Điểm CB": None, "Setup": "", "RSI": None,
           "Xu hướng": "", "Giá": None, "P/E": None, "ROE%": None,
           "Cảnh báo": 0, "Gió ngành": "", "_err": []}
    if raw.get("err"):
        row["_err"].append(raw["err"])
    try:
        cur, _ = A.extract_metrics(raw.get("ratio"))
        # điểm rút gọn cho bảng: chỉ dùng sinh lời + sức khỏe + định giá (bỏ growth/cf)
        sc = A.score_stock(cur, {}, {})
        warns = A.detect_warnings(cur, {}, {})
        setup = MK.entry_setup(raw.get("hist"))

        row["Điểm CB"] = sc["total"]
        row["P/E"] = round(cur["pe"], 1) if cur.get("pe") else None
        row["ROE%"] = round(cur["roe"], 1) if cur.get("roe") else None
        row["RSI"] = setup.get("rsi")
        row["Xu hướng"] = setup.get("trend") or ""
        row["Giá"] = setup.get("price")
        row["Cảnh báo"] = len(warns)
        row["status"] = setup.get("status", "THEODOI")
        row["Setup"] = setup["reasons"][0] if setup.get("reasons") else ""
        if row["Ngành"] in favored_sectors:
            row["Gió ngành"] = "✅ thuận"
        row["Trạng thái"] = STATUS_LABEL.get(row["status"], "")
    except Exception as ex:
        row["_err"].append(f"{type(ex).__name__}: {ex}")
    return row


def rank_key(row):
    st = STATUS_ORDER.get(row.get("status"), 9)
    cb = row.get("Điểm CB") or 0
    wind = 1 if row.get("Gió ngành") else 0
    return (st, -wind, -cb)


def run_screen(symbols, period, source, favored_sectors=None, progress_cb=None, max_workers=8):
    """Quét song song. Trả danh sách row đã xếp hạng."""
    favored_sectors = favored_sectors or set()
    rows = []
    done = 0
    n = len(symbols)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_map = {ex.submit(_fetch_raw, s, period, source): s for s in symbols}
        for fut in as_completed(future_map):
            sym = future_map[fut]
            try:
                raw = fut.result()
            except Exception as e:
                raw = {"ratio": None, "hist": None, "err": f"{type(e).__name__}"}
            rows.append(_process(sym, raw, favored_sectors))
            done += 1
            if progress_cb:
                progress_cb(done / n, sym)
    rows.sort(key=rank_key)
    return rows
