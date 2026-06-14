# -*- coding: utf-8 -*-
"""
Bộ chỉ báo kỹ thuật — ÁP Y CHANG thông số app vàng (XAU) khung lớn.
- Stochastic (42, 5, 3)
- MACD (24, 52, 14)
- ADX + DI (mặc định 14)
- EMA 200 / 1200
- Fibonacci retracement + extension 161.8%

Công thức theo chuẩn TradingView. Tính trên khung Ngày (D1).
"""
import numpy as np
import pandas as pd
from data import pick_col


def _ohlc(df):
    """Chuẩn hóa cột OHLC từ df (dchart/vnstock)."""
    o = pick_col(df, ["open"], contains=True)
    h = pick_col(df, ["high"], contains=True)
    l = pick_col(df, ["low"], contains=True)
    c = pick_col(df, ["close"], contains=True)
    v = pick_col(df, ["volume"], contains=True)
    t = pick_col(df, ["time", "date", "tradingdate"], contains=True)
    out = pd.DataFrame()
    out["open"] = pd.to_numeric(df[o], errors="coerce") if o else None
    out["high"] = pd.to_numeric(df[h], errors="coerce") if h else None
    out["low"] = pd.to_numeric(df[l], errors="coerce") if l else None
    out["close"] = pd.to_numeric(df[c], errors="coerce")
    out["volume"] = pd.to_numeric(df[v], errors="coerce") if v else 0
    if t:
        out["time"] = pd.to_datetime(df[t], errors="coerce")
    else:
        out["time"] = pd.to_datetime(df.index, errors="coerce")
    return out.reset_index(drop=True)


def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


def macd(close, fast=24, slow=52, signal=14):
    """MACD (24,52,14) — thông số app vàng."""
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def stochastic(high, low, close, k=42, smooth_k=5, d=3):
    """Stochastic (42,5,3) — thông số app vàng.
    %K = SMA(raw %K, smooth_k); %D = SMA(%K, d)."""
    ll = low.rolling(k).min()
    hh = high.rolling(k).max()
    raw_k = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    pK = raw_k.rolling(smooth_k).mean()
    pD = pK.rolling(d).mean()
    return pK, pD


def adx(high, low, close, period=14):
    """ADX + DI+ / DI- theo Wilder."""
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=high.index).ewm(alpha=1/period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=high.index).ewm(alpha=1/period, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_line = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx_line, plus_di, minus_di


def add_indicators(df, macd_p=(24,52,14), stoch_p=(42,5,3), adx_p=14,
                   ema_lens=(200, 1200)):
    """Thêm tất cả chỉ báo vào df chuẩn hóa. Trả df mới."""
    d = _ohlc(df).copy()
    c, h, l = d["close"], d["high"], d["low"]
    for L in ema_lens:
        d[f"ema{L}"] = ema(c, L)
    d["macd"], d["macd_signal"], d["macd_hist"] = macd(c, *macd_p)
    d["stoch_k"], d["stoch_d"] = stochastic(h, l, c, *stoch_p)
    d["adx"], d["di_plus"], d["di_minus"] = adx(h, l, c, adx_p)
    return d


def weekly_resample(df):
    """Gộp D1 -> W1 KHỚP TradingView: tuần kết thúc Thứ Sáu (phiên cuối TTCK VN),
    nhãn theo ngày đầu nến. Open=phiên đầu tuần, High/Low=max/min, Close=phiên cuối."""
    d = _ohlc(df).copy()
    d = d.set_index("time").sort_index()
    # W-FRI: tuần kết thúc Thứ Sáu (khớp lịch giao dịch & TradingView)
    rule = "W-FRI"
    w = pd.DataFrame()
    w["open"] = d["open"].resample(rule).first()
    w["high"] = d["high"].resample(rule).max()
    w["low"] = d["low"].resample(rule).min()
    w["close"] = d["close"].resample(rule).last()
    w["volume"] = d["volume"].resample(rule).sum()
    w = w.dropna(subset=["close"])
    # đổi nhãn: TradingView gắn nến tuần theo NGÀY ĐẦU tuần (Thứ Hai) thay vì cuối
    w.index = w.index - pd.Timedelta(days=4)
    return w.reset_index()


def fibonacci_levels(df, lookback=120):
    """Fibo retracement từ swing low->high (hoặc high->low) trong N phiên gần nhất.
    Trả dict {level_name: price, direction, swing_high, swing_low}."""
    d = _ohlc(df).tail(lookback)
    if d.empty:
        return None
    hi = float(d["high"].max()); lo = float(d["low"].min())
    idx_hi = d["high"].idxmax(); idx_lo = d["low"].idxmin()
    # hướng: nếu đỉnh tới sau đáy -> sóng tăng (retrace từ trên xuống)
    uptrend = idx_hi > idx_lo
    diff = hi - lo
    ratios = {"0.0": 0.0, "0.236": 0.236, "0.382": 0.382, "0.5": 0.5,
              "0.618": 0.618, "0.786": 0.786, "1.0": 1.0, "1.618": 1.618}
    levels = {}
    for name, r in ratios.items():
        if uptrend:
            # retrace tính từ đỉnh xuống
            levels[name] = hi - diff * r
        else:
            levels[name] = lo + diff * r
    return {"levels": levels, "uptrend": uptrend, "high": hi, "low": lo,
            "ext_1618": (hi + diff*0.618) if uptrend else (lo - diff*0.618)}


def trend_strength(d):
    """Đọc ADX để mô tả sức mạnh xu hướng (dòng cuối)."""
    try:
        a = float(d["adx"].iloc[-1])
        dp = float(d["di_plus"].iloc[-1]); dm = float(d["di_minus"].iloc[-1])
        if a < 20: strg = "Xu hướng yếu / đi ngang"
        elif a < 25: strg = "Xu hướng đang hình thành"
        elif a < 40: strg = "Xu hướng mạnh"
        else: strg = "Xu hướng rất mạnh"
        direction = "tăng" if dp > dm else "giảm"
        return f"ADX {a:.0f} — {strg} (thiên {direction})", a, dp, dm
    except Exception:
        return "ADX: chưa đủ dữ liệu", None, None, None


def wait_zone(df, lookback=120):
    """Tính VÙNG CHỜ (khoảng giá để canh vào) bằng cách TỔNG HỢP:
    Fibo retrace (0.382/0.5/0.618) + EMA200 + đáy hỗ trợ cũ.
    Gom các mức gần nhau (±1.5%) thành vùng; vùng nhiều yếu tố = mạnh nhất.
    Trả: {low, high, mid, factors[], strength, dist_pct} hoặc None."""
    d = _ohlc(df)
    if len(d) < 60:
        return None
    last = float(d["close"].iloc[-1])
    candidates = []

    fib = fibonacci_levels(df, lookback)
    if fib and fib.get("levels"):
        for nm in ["0.382", "0.5", "0.618"]:
            if nm in fib["levels"]:
                candidates.append((fib["levels"][nm], f"Fibo {nm}"))

    e200 = ema(d["close"], 200)
    if e200.notna().iloc[-1]:
        candidates.append((float(e200.iloc[-1]), "EMA200"))

    win = d.tail(lookback).reset_index(drop=True)
    lows = win["low"]
    for i in range(2, len(lows) - 2):
        if (lows[i] <= lows[i-1] and lows[i] <= lows[i-2]
                and lows[i] <= lows[i+1] and lows[i] <= lows[i+2]):
            candidates.append((float(lows[i]), "Đáy cũ"))

    candidates = [(p, n) for p, n in candidates if p is not None and abs(p - last) / last < 0.06]
    if not candidates:
        return None

    candidates.sort()
    clusters = []
    cur = [candidates[0]]
    for p, n in candidates[1:]:
        if abs(p - cur[-1][0]) / cur[-1][0] < 0.015:
            cur.append((p, n))
        else:
            clusters.append(cur); cur = [(p, n)]
    clusters.append(cur)

    best = None
    for cl in clusters:
        prices = [p for p, _ in cl]
        mid = sum(prices) / len(prices)
        factors = list(dict.fromkeys([n for _, n in cl]))
        score = len(factors)
        dist = abs(last - mid) / last
        rank = (score, -dist)
        if best is None or rank > best["_rank"]:
            best = {"low": round(min(prices), 2), "high": round(max(prices), 2),
                    "mid": round(mid, 2), "factors": factors,
                    "strength": score, "_rank": rank, "dist_pct": round(dist*100, 1)}
    if best:
        best.pop("_rank", None)
        if best["low"] == best["high"]:
            best["low"] = round(best["low"] * 0.993, 2)
            best["high"] = round(best["high"] * 1.007, 2)
    return best


def pct_changes(df):
    """Tính % thay đổi giá theo mốc: 1 tuần, 1 tháng, 3 tháng, 6 tháng, YTD.
    Dựa trên số phiên giao dịch xấp xỉ (5/22/66/132 phiên) + đầu năm.
    Trả dict {'1W','1M','3M','6M','YTD'} (% làm tròn 1 chữ số) hoặc None."""
    d = _ohlc(df)
    if len(d) < 5:
        return None
    c = d["close"].reset_index(drop=True)
    last = float(c.iloc[-1])
    def chg(n_back):
        if len(c) > n_back:
            old = float(c.iloc[-1 - n_back])
            if old > 0:
                return round((last - old) / old * 100, 1)
        return None
    out = {"1W": chg(5), "1M": chg(22), "3M": chg(66), "6M": chg(132)}
    # YTD: tìm phiên đầu tiên của năm hiện tại
    try:
        t = pd.to_datetime(d["time"])
        yr = t.iloc[-1].year
        mask = t.dt.year == yr
        if mask.any():
            first_close = float(d.loc[mask, "close"].iloc[0])
            if first_close > 0:
                out["YTD"] = round((last - first_close) / first_close * 100, 1)
    except Exception:
        out["YTD"] = None
    return out
