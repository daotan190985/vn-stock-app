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
    """VNDirect là chính (giá ổn định, chỉ số best-effort); vnstock dự phòng. An toàn đa luồng."""
    import vndirect as VND
    out = {"ratio": None, "hist": None, "err": None, "src": "VNDirect"}
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=320)).strftime("%Y-%m-%d")

    # --- giá: VNDirect dchart (chính) -> vnstock (phụ) ---
    out["hist"] = VND.vnd_history(sym, start, end)
    if out["hist"] is None:
        try:
            from vnstock.api.quote import Quote
            q = Quote(symbol=sym.upper(), source=source, random_agent=True)
            h = q.history(start=start, end=end, interval="1D")
            if h is not None and not h.empty:
                out["hist"] = h; out["src"] = "vnstock"
        except Exception as e:
            out["err"] = f"hist: {type(e).__name__}"

    # --- chỉ số: VNDirect finfo (best-effort) -> vnstock (phụ) ---
    out["ratio"] = VND.vnd_ratios_df(sym)
    if out["ratio"] is None:
        try:
            from vnstock.api.financial import Finance
            f = Finance(source=source, symbol=sym.upper(), period=period)
            r = f.ratio(lang="en", dropna=False)
            if r is not None and not r.empty:
                out["ratio"] = r
        except Exception:
            pass
    return out


def _process(sym, raw, favored_sectors):
    """Tính toán nhẹ (CPU) từ dữ liệu thô — không gọi mạng."""
    import fundamentals as FUND
    favored_sectors = favored_sectors or set()
    row = {"Mã": sym, "Ngành": sector_of(sym), "status": "THEODOI",
           "Trạng thái": "", "Điểm CB": None, "Setup": "", "RSI": None,
           "Xu hướng": "", "Giá": None, "P/E": None, "ROE%": None,
           "Cảnh báo": 0, "Gió ngành": "", "Vùng chờ": "", "Vùng": "",
           "%1M": None, "%3M": None, "%6M": None, "%YTD": None, "_err": []}
    if raw.get("err"):
        row["_err"].append(raw["err"])
    try:
        # chỉ số: ưu tiên live (VNDirect/vnstock); thiếu -> đọc cache fundamentals.json
        cur, _ = A.extract_metrics(raw.get("ratio"))
        if not cur or all(v is None for v in cur.values()):
            cur = FUND.get_metrics(sym)
        growth = FUND.get_growth(sym)
        cf = FUND.get_cashflow(sym)

        sc = A.score_stock(cur, growth, cf)
        warns = A.detect_warnings(cur, growth, cf)
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
        # Vùng chờ + cảnh báo chạm vùng
        wz = setup.get("wait_zone")
        if wz:
            row["Vùng chờ"] = f"{wz['low']:,.2f}–{wz['high']:,.2f}"
            if setup.get("zone_alert"):
                row["Vùng"] = setup["zone_alert"]
        if row["Ngành"] in favored_sectors:
            row["Gió ngành"] = "✅ thuận"
        row["Trạng thái"] = STATUS_LABEL.get(row["status"], "")
        # % thay đổi theo mốc thời gian
        try:
            import indicators as IND
            pc = IND.pct_changes(raw.get("hist"))
            if pc:
                row["%1M"] = pc.get("1M"); row["%3M"] = pc.get("3M")
                row["%6M"] = pc.get("6M"); row["%YTD"] = pc.get("YTD")
        except Exception:
            pass
    except Exception as ex:
        row["_err"].append(f"{type(ex).__name__}: {ex}")
    return row


def rank_key(row):
    st = STATUS_ORDER.get(row.get("status"), 9)
    cb = row.get("Điểm CB") or 0
    wind = 1 if row.get("Gió ngành") else 0
    return (st, -wind, -cb)


def apply_market_filter(rows, market_ok):
    """Khi thị trường thanh khoản YẾU (market_ok=False): hạ mọi VAO -> CHO."""
    if market_ok:
        return rows
    for r in rows:
        if r.get("status") == "VAO":
            r["status"] = "CHO"
            r["Trạng thái"] = STATUS_LABEL["CHO"]
            r["Setup"] = "TT thanh khoản yếu (<ngưỡng) — không vào, chờ thị trường khỏe. | " + (r.get("Setup") or "")
    rows.sort(key=rank_key)
    return rows


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
