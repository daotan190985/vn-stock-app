# -*- coding: utf-8 -*-
"""
Cơ chế sàn giao dịch VN + Trạng thái mã so với biểu đồ nến.

1) Trần / Sàn / Tham chiếu theo biên độ từng sàn:
   - HOSE  : ±7%
   - HNX   : ±10%
   - UPCoM : ±15%
   (Ngày chào sàn / sau nghỉ dài có biên độ khác — đây là biên độ thường ngày.)

2) Trạng thái kỹ thuật suy ra TRỰC TIẾP từ chuỗi nến (OHLC) — rule-based,
   không dùng chỉ báo "hộp đen". Mọi nhận định kèm số liệu để kiểm chứng.
"""
import pandas as pd
import numpy as np
from data import pick_col

BANDS = {"HOSE": 0.07, "HSX": 0.07, "HNX": 0.10, "UPCOM": 0.15, "UPCOM ": 0.15}


def round_tick(price, exchange="HOSE"):
    """Làm tròn theo bước giá HOSE (đồng). HNX/UPCoM bước 100đ."""
    if price is None:
        return None
    ex = (exchange or "HOSE").upper()
    if ex in ("HNX", "UPCOM"):
        step = 100
    else:
        # HOSE: <10k =>10đ, 10k-50k =>50đ, >=50k =>100đ
        if price < 10000: step = 10
        elif price < 50000: step = 50
        else: step = 100
    return round(price / step) * step


def ceiling_floor(ref_price, exchange="HOSE"):
    """Tính trần/sàn từ giá tham chiếu theo biên độ sàn."""
    if ref_price is None or ref_price <= 0:
        return None, None
    band = BANDS.get((exchange or "HOSE").upper(), 0.07)
    ceil = round_tick(ref_price * (1 + band), exchange)
    floor = round_tick(ref_price * (1 - band), exchange)
    return ceil, floor


def parse_price_board(board_df, exchange="HOSE"):
    """Đọc bảng giá vnstock -> dict {ref, ceil, floor, match}. Tự tính nếu thiếu."""
    out = {"ref": None, "ceil": None, "floor": None, "match": None, "exchange": exchange}
    if board_df is None or board_df.empty:
        return out
    row = board_df.reset_index(drop=True).iloc[0]

    def g(cands):
        c = pick_col(board_df, cands, contains=True)
        if c is None:
            return None
        try:
            v = row[c]
            return float(v) if pd.notna(v) else None
        except Exception:
            return None

    out["ref"]   = g(["ref_price", "reference", "tham chiếu", "ref"])
    out["ceil"]  = g(["ceiling", "ceil", "trần"])
    out["floor"] = g(["floor", "sàn"])
    out["match"] = g(["match_price", "last_price", "close_price", "khớp lệnh", "giá khớp", "last"])

    # vnstock đôi khi trả giá theo nghìn đồng -> chuẩn hóa nếu nghi ngờ
    # (bỏ qua, để nguyên — người dùng đối chiếu TradingView)

    # Tự tính trần/sàn nếu thiếu mà có tham chiếu
    if out["ref"] and (out["ceil"] is None or out["floor"] is None):
        c, f = ceiling_floor(out["ref"], exchange)
        out["ceil"] = out["ceil"] or c
        out["floor"] = out["floor"] or f
    return out


# ----------------- TRẠNG THÁI THEO NẾN -----------------

def candle_status(hist_df, board=None, lookback=60):
    """
    Phân tích trạng thái mã từ chuỗi nến gần nhất.
    Trả về dict: {price, trend, position, signals[], summary}
    Tất cả rule-based, kèm số liệu.
    """
    res = {"price": None, "trend": None, "position": None, "signals": [], "summary": ""}
    if hist_df is None or hist_df.empty:
        res["summary"] = "Không có dữ liệu nến."
        return res

    df = hist_df.copy()
    o = pick_col(df, ["open"], contains=True)
    h = pick_col(df, ["high"], contains=True)
    l = pick_col(df, ["low"], contains=True)
    c = pick_col(df, ["close"], contains=True)
    v = pick_col(df, ["volume"], contains=True)
    if c is None:
        res["summary"] = "Thiếu cột giá đóng cửa."
        return res

    df = df.tail(lookback).reset_index(drop=True)
    close = pd.to_numeric(df[c], errors="coerce")
    high = pd.to_numeric(df[h], errors="coerce") if h else close
    low = pd.to_numeric(df[l], errors="coerce") if l else close
    vol = pd.to_numeric(df[v], errors="coerce") if v else None

    last = float(close.iloc[-1])
    res["price"] = last

    # --- Xu hướng: MA20 vs MA50 + độ dốc ---
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    m20 = ma20.iloc[-1] if pd.notna(ma20.iloc[-1]) else None
    m50 = ma50.iloc[-1] if pd.notna(ma50.iloc[-1]) else None
    if m20 and m50:
        if last > m20 > m50:
            res["trend"] = "Tăng (uptrend)"
        elif last < m20 < m50:
            res["trend"] = "Giảm (downtrend)"
        else:
            res["trend"] = "Đi ngang / chuyển tiếp"
        res["signals"].append(f"Giá {last:,.0f} | MA20 {m20:,.0f} | MA50 {m50:,.0f}")
    elif m20:
        res["trend"] = "Tăng" if last > m20 else "Giảm"

    # --- Vị trí trong biên độ N phiên ---
    win = close.tail(min(lookback, len(close)))
    hi = float(high.tail(len(win)).max())
    lo = float(low.tail(len(win)).min())
    if hi > lo:
        pos_pct = (last - lo) / (hi - lo) * 100
        res["position"] = pos_pct
        if pos_pct >= 90:
            res["signals"].append(f"Sát đỉnh {lookback} phiên ({pos_pct:.0f}% biên độ) — vùng kháng cự.")
        elif pos_pct <= 10:
            res["signals"].append(f"Sát đáy {lookback} phiên ({pos_pct:.0f}% biên độ) — vùng hỗ trợ.")
        else:
            res["signals"].append(f"Ở {pos_pct:.0f}% biên độ {lookback} phiên (đỉnh {hi:,.0f} / đáy {lo:,.0f}).")

    # --- Breakout / Breakdown đỉnh-đáy 20 phiên ---
    hi20 = float(high.iloc[-21:-1].max()) if len(high) > 21 else None
    lo20 = float(low.iloc[-21:-1].min()) if len(low) > 21 else None
    if hi20 and last > hi20:
        res["signals"].append(f"⤴ Breakout vượt đỉnh 20 phiên ({hi20:,.0f}).")
    if lo20 and last < lo20:
        res["signals"].append(f"⤵ Breakdown thủng đáy 20 phiên ({lo20:,.0f}).")

    # --- Khối lượng đột biến ---
    if vol is not None and len(vol) >= 20:
        vavg = vol.tail(20).mean()
        vlast = vol.iloc[-1]
        if pd.notna(vavg) and vavg > 0 and pd.notna(vlast):
            ratio = vlast / vavg
            if ratio >= 2:
                res["signals"].append(f"Khối lượng đột biến ×{ratio:.1f} trung bình 20 phiên.")
            elif ratio <= 0.5:
                res["signals"].append(f"Thanh khoản cạn (×{ratio:.1f} TB20) — kém quan tâm.")

    # --- So với trần/sàn/tham chiếu (nếu có bảng giá) ---
    if board:
        ceil, floor, ref = board.get("ceil"), board.get("floor"), board.get("ref")
        if ceil and last >= ceil * 0.995:
            res["signals"].append(f"🔴 Áp sát/đạt GIÁ TRẦN ({ceil:,.0f}).")
        elif floor and last <= floor * 1.005:
            res["signals"].append(f"🔵 Áp sát/đạt GIÁ SÀN ({floor:,.0f}).")
        if ref:
            chg = (last - ref) / ref * 100
            res["signals"].append(f"So tham chiếu {ref:,.0f}: {chg:+.2f}%.")

    # --- Tổng hợp ---
    parts = []
    if res["trend"]:
        parts.append(f"Xu hướng: {res['trend']}")
    if res["position"] is not None:
        if res["position"] >= 90: parts.append("đang ở vùng đỉnh")
        elif res["position"] <= 10: parts.append("đang ở vùng đáy")
        else: parts.append("ở vùng giữa")
    res["summary"] = " — ".join(parts) if parts else "Chưa đủ dữ liệu kết luận."
    return res


def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def entry_setup(hist_df, board=None):
    """
    Phát hiện ĐIỂM VÀO LỆNH cho cổ phiếu trên khung Daily (kiểu swing/position).
    Logic tương tự app vàng: ưu tiên thuận xu hướng, vào ở vùng hỗ trợ/pullback,
    không đu đỉnh. Trả về:
      status: 'VAO' | 'CHO' | 'THEODOI' | 'TRANH'
      reasons[], rsi, dist_ma20, dist_ma50, trend
    """
    out = {"status": "THEODOI", "reasons": [], "rsi": None,
           "trend": None, "price": None, "support": None, "resistance": None}
    if hist_df is None or hist_df.empty:
        out["reasons"].append("Thiếu dữ liệu giá."); return out

    df = hist_df.copy()
    cc = pick_col(df, ["close"], contains=True)
    hh = pick_col(df, ["high"], contains=True)
    ll = pick_col(df, ["low"], contains=True)
    vv = pick_col(df, ["volume"], contains=True)
    if cc is None:
        out["reasons"].append("Thiếu giá đóng cửa."); return out

    df = df.tail(260).reset_index(drop=True)
    close = pd.to_numeric(df[cc], errors="coerce")
    high = pd.to_numeric(df[hh], errors="coerce") if hh else close
    low = pd.to_numeric(df[ll], errors="coerce") if ll else close
    vol = pd.to_numeric(df[vv], errors="coerce") if vv else None
    if len(close) < 60:
        out["reasons"].append("Chuỗi giá quá ngắn (<60 phiên)."); return out

    last = float(close.iloc[-1]); out["price"] = last
    ma20 = close.rolling(20).mean(); ma50 = close.rolling(50).mean(); ma200 = close.rolling(200).mean()
    m20 = ma20.iloc[-1]; m50 = ma50.iloc[-1]; m200 = ma200.iloc[-1]
    rsi = _rsi(close).iloc[-1]; out["rsi"] = round(float(rsi), 1) if pd.notna(rsi) else None

    # Xu hướng nền
    up = pd.notna(m200) and last > m200 and pd.notna(m50) and m50 >= m200
    down = pd.notna(m200) and last < m200 and pd.notna(m50) and m50 < m200
    if up: out["trend"] = "Tăng"
    elif down: out["trend"] = "Giảm"
    else: out["trend"] = "Đi ngang"

    # Hỗ trợ / kháng cự gần (đáy/đỉnh 20 phiên)
    sup = float(low.iloc[-21:-1].min()) if len(low) > 21 else None
    res = float(high.iloc[-21:-1].max()) if len(high) > 21 else None
    out["support"] = sup; out["resistance"] = res

    dist20 = (last - m20) / m20 * 100 if pd.notna(m20) else None
    dist50 = (last - m50) / m50 * 100 if pd.notna(m50) else None

    # Khối lượng
    vratio = None
    if vol is not None and len(vol) >= 20:
        va = vol.tail(20).mean()
        if pd.notna(va) and va > 0:
            vratio = vol.iloc[-1] / va

    # ----- LUẬT XÁC ĐỊNH ĐIỂM VÀO -----
    if down:
        out["status"] = "TRANH"
        out["reasons"].append("Xu hướng nền GIẢM (giá < MA200, MA50 < MA200) — không vào thuận lý.")
        return out

    setup_score = 0
    # 1) Pullback về MA20/MA50 trong uptrend = vùng vào đẹp
    if up and dist20 is not None and -3 <= dist20 <= 3:
        setup_score += 2
        out["reasons"].append(f"Pullback sát MA20 ({dist20:+.1f}%) trong uptrend — vùng vào thuận xu hướng.")
    elif up and dist50 is not None and -3 <= dist50 <= 5:
        setup_score += 2
        out["reasons"].append(f"Giá về quanh MA50 ({dist50:+.1f}%) — hỗ trợ động trong uptrend.")

    # 2) RSI quá bán trong uptrend = bật nảy
    if up and out["rsi"] is not None and out["rsi"] < 40:
        setup_score += 1
        out["reasons"].append(f"RSI {out['rsi']} thấp trong uptrend — khả năng bật nảy.")

    # 3) Test hỗ trợ (giá sát đáy 20 phiên mà chưa thủng)
    if sup and last <= sup * 1.02 and last >= sup * 0.99:
        setup_score += 1
        out["reasons"].append(f"Đang test hỗ trợ {sup:,.0f} (đáy 20 phiên) — chờ nến xác nhận giữ.")

    # 4) Breakout kháng cự kèm volume
    if res and last > res and vratio and vratio >= 1.5:
        setup_score += 2
        out["reasons"].append(f"Breakout vượt {res:,.0f} kèm KL ×{vratio:.1f} — điểm vào động lượng.")
    elif res and last > res:
        out["reasons"].append(f"Vượt kháng cự {res:,.0f} nhưng KL chưa xác nhận — rủi ro phá giả.")

    # 5) Đu đỉnh: giá xa MA20 (>12%) = KHÔNG vào, chờ chỉnh
    if dist20 is not None and dist20 > 12:
        out["reasons"].append(f"Giá cách MA20 +{dist20:.1f}% — quá xa, RỦI RO đu đỉnh, chờ chỉnh.")
        out["status"] = "CHO"
        return out

    # 6) RSI quá mua (>70): dù thuận xu hướng cũng KHÔNG vào mới, chờ hạ nhiệt
    if out["rsi"] is not None and out["rsi"] > 70:
        out["reasons"].insert(0, f"RSI {out['rsi']} quá mua (>70) — không vào mới, chờ RSI hạ nhiệt/pullback.")
        out["status"] = "CHO"
        return out

    # 7) THANH KHOẢN MÃ CẠN: pullback đẹp nhưng KL < 0.5x TB20 -> chưa vào, chờ dòng tiền
    if setup_score >= 2 and vratio is not None and vratio < 0.5:
        out["reasons"].insert(0, f"Thanh khoản cạn (×{vratio:.1f} TB20) — chưa có dòng tiền xác nhận, hạ xuống CHỜ.")
        out["status"] = "CHO"
        return out

    # Kết luận
    if setup_score >= 2:
        out["status"] = "VAO"
    elif up:
        out["status"] = "CHO"
        if not out["reasons"]:
            out["reasons"].append("Uptrend nhưng chưa về vùng vào đẹp — chờ pullback.")
    else:
        out["status"] = "THEODOI"
        out["reasons"].append("Đi ngang — chờ xác nhận xu hướng trước khi vào.")
    return out
