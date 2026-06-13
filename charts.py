# -*- coding: utf-8 -*-
"""
Vẽ biểu đồ Plotly đa tầng — phong cách app vàng (dark, chuyên nghiệp).
Hỗ trợ BẬT/TẮT từng chỉ báo và TỰ CO số tầng (chỉ vẽ tầng được bật).
Tầng giá luôn có (Nến + EMA + Fibo). MACD/Stoch/ADX bật/tắt tùy chọn.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DARK_BG = "#0e1117"
GRID = "#222"


def build_chart(d, fib=None, title="", height=None,
                show_ema=True, show_macd=True, show_stoch=True, show_adx=True,
                wait_zone=None):
    # quyết định các tầng phụ được bật
    sub = []
    if show_macd: sub.append("macd")
    if show_stoch: sub.append("stoch")
    if show_adx: sub.append("adx")

    n_rows = 1 + len(sub)
    # chiều cao tầng giá lớn, tầng phụ nhỏ — tự co theo số tầng
    price_h = 0.55 if sub else 1.0
    rest = (1 - price_h) / len(sub) if sub else 0
    row_heights = [price_h] + [rest] * len(sub)
    titles = ["Giá + EMA + Fibonacci"] + [
        {"macd": "MACD (24,52,14)", "stoch": "Stochastic (42,5,3)", "adx": "ADX + DI"}[s]
        for s in sub]

    fig = make_subplots(rows=n_rows, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03, row_heights=row_heights,
                        subplot_titles=titles)
    x = d["time"]

    # --- Tầng 1: Nến ---
    fig.add_trace(go.Candlestick(
        x=x, open=d["open"], high=d["high"], low=d["low"], close=d["close"],
        name="Giá", increasing_line_color="#26a69a", decreasing_line_color="#ef5350"),
        row=1, col=1)
    # đường dóng giá hiện tại (giống TradingView)
    try:
        last_price = float(d["close"].iloc[-1])
        fig.add_hline(y=last_price, line=dict(color="#e0e0e0", width=1, dash="dash"),
                      row=1, col=1, annotation_text=f" {last_price:,.2f}",
                      annotation_position="right",
                      annotation_font=dict(size=11, color="#000"),
                      annotation_bgcolor="#e0e0e0")
    except Exception:
        pass

    # --- Vùng chờ (dải mờ) ---
    if wait_zone and wait_zone.get("low") and wait_zone.get("high"):
        fig.add_hrect(y0=wait_zone["low"], y1=wait_zone["high"],
                      fillcolor="#2962ff", opacity=0.12, line_width=0, row=1, col=1,
                      annotation_text=f"Vùng chờ {wait_zone['low']:,.2f}–{wait_zone['high']:,.2f}",
                      annotation_position="top left",
                      annotation_font=dict(size=10, color="#7da9ff"))
    if show_ema:
        if "ema200" in d:
            fig.add_trace(go.Scatter(x=x, y=d["ema200"], name="EMA200",
                          line=dict(color="#f5c518", width=1.2)), row=1, col=1)
        if "ema1200" in d:
            fig.add_trace(go.Scatter(x=x, y=d["ema1200"], name="EMA1200",
                          line=dict(color="#ab47bc", width=1.2)), row=1, col=1)

    if fib and fib.get("levels"):
        fib_colors = {"0.0":"#888","0.236":"#26a69a","0.382":"#66bb6a",
                      "0.5":"#ffa726","0.618":"#ef5350","0.786":"#ec407a",
                      "1.0":"#888","1.618":"#7e57c2"}
        for name, price in fib["levels"].items():
            fig.add_hline(y=price, line=dict(color=fib_colors.get(name,"#666"),
                          width=0.8, dash="dot"), row=1, col=1,
                          annotation_text=f"Fib {name} · {price:,.2f}",
                          annotation_position="right",
                          annotation_font=dict(size=9, color=fib_colors.get(name,"#999")))

    # --- các tầng phụ ---
    r = 2
    for s in sub:
        if s == "macd":
            colors = ["#26a69a" if v >= 0 else "#ef5350" for v in d["macd_hist"].fillna(0)]
            fig.add_trace(go.Bar(x=x, y=d["macd_hist"], name="Hist", marker_color=colors), row=r, col=1)
            fig.add_trace(go.Scatter(x=x, y=d["macd"], name="MACD",
                          line=dict(color="#42a5f5", width=1)), row=r, col=1)
            fig.add_trace(go.Scatter(x=x, y=d["macd_signal"], name="Signal",
                          line=dict(color="#ffa726", width=1)), row=r, col=1)
        elif s == "stoch":
            fig.add_trace(go.Scatter(x=x, y=d["stoch_k"], name="%K",
                          line=dict(color="#42a5f5", width=1)), row=r, col=1)
            fig.add_trace(go.Scatter(x=x, y=d["stoch_d"], name="%D",
                          line=dict(color="#ffa726", width=1)), row=r, col=1)
            fig.add_hline(y=80, line=dict(color="#ef5350", width=0.6, dash="dash"), row=r, col=1)
            fig.add_hline(y=20, line=dict(color="#26a69a", width=0.6, dash="dash"), row=r, col=1)
        elif s == "adx":
            fig.add_trace(go.Scatter(x=x, y=d["adx"], name="ADX",
                          line=dict(color="#f5c518", width=1.3)), row=r, col=1)
            fig.add_trace(go.Scatter(x=x, y=d["di_plus"], name="DI+",
                          line=dict(color="#26a69a", width=1)), row=r, col=1)
            fig.add_trace(go.Scatter(x=x, y=d["di_minus"], name="DI-",
                          line=dict(color="#ef5350", width=1)), row=r, col=1)
            fig.add_hline(y=25, line=dict(color="#888", width=0.6, dash="dash"), row=r, col=1)
        r += 1

    if height is None:
        height = 420 + 150 * len(sub)  # tự co theo số tầng -> khớp màn hình

    fig.update_layout(
        template="plotly_dark", height=height, title=title,
        paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=10, r=70, t=50, b=10), dragmode="pan",
        hovermode="x unified", autosize=True)
    for rr in range(1, n_rows + 1):
        fig.update_xaxes(gridcolor=GRID, row=rr, col=1)
        fig.update_yaxes(gridcolor=GRID, row=rr, col=1)
    return fig
