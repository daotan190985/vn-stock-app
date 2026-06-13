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
    """Gộp D1 -> W1 (khung lớn) để xác định xu hướng & Fibo lớn."""
    d = _ohlc(df).copy()
    d = d.set_index("time")
    w = pd.DataFrame()
    w["open"] = d["open"].resample("W").first()
    w["high"] = d["high"].resample("W").max()
    w["low"] = d["low"].resample("W").min()
    w["close"] = d["close"].resample("W").last()
    w["volume"] = d["volume"].resample("W").sum()
    return w.dropna().reset_index()


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
