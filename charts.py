# -*- coding: utf-8 -*-
"""
Vẽ biểu đồ Plotly đa tầng — phong cách app vàng (dark, chuyên nghiệp).
Tầng 1: Nến + EMA200/1200 + Fibonacci
Tầng 2: MACD (24,52,14) — histogram + line
Tầng 3: Stochastic (42,5,3) — %K %D + vùng 20/80
Tầng 4: ADX + DI+ DI-
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DARK_BG = "#0e1117"
GRID = "#222"

def build_chart(d, fib=None, title="", height=820):
    """d: DataFrame đã add_indicators. fib: dict từ fibonacci_levels."""
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.5, 0.18, 0.16, 0.16],
        subplot_titles=("Giá + EMA + Fibonacci", "MACD (24,52,14)",
                        "Stochastic (42,5,3)", "ADX + DI"))

    x = d["time"]

    # --- Tầng 1: Nến ---
    fig.add_trace(go.Candlestick(
        x=x, open=d["open"], high=d["high"], low=d["low"], close=d["close"],
        name="Giá", increasing_line_color="#26a69a", decreasing_line_color="#ef5350"),
        row=1, col=1)
    if "ema200" in d:
        fig.add_trace(go.Scatter(x=x, y=d["ema200"], name="EMA200",
                      line=dict(color="#f5c518", width=1.2)), row=1, col=1)
    if "ema1200" in d:
        fig.add_trace(go.Scatter(x=x, y=d["ema1200"], name="EMA1200",
                      line=dict(color="#ab47bc", width=1.2)), row=1, col=1)

    # --- Fibonacci (kẻ ngang trên tầng giá) ---
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

    # --- Tầng 2: MACD ---
    colors = ["#26a69a" if v >= 0 else "#ef5350" for v in d["macd_hist"].fillna(0)]
    fig.add_trace(go.Bar(x=x, y=d["macd_hist"], name="Hist", marker_color=colors),
                  row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=d["macd"], name="MACD",
                  line=dict(color="#42a5f5", width=1)), row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=d["macd_signal"], name="Signal",
                  line=dict(color="#ffa726", width=1)), row=2, col=1)

    # --- Tầng 3: Stochastic ---
    fig.add_trace(go.Scatter(x=x, y=d["stoch_k"], name="%K",
                  line=dict(color="#42a5f5", width=1)), row=3, col=1)
    fig.add_trace(go.Scatter(x=x, y=d["stoch_d"], name="%D",
                  line=dict(color="#ffa726", width=1)), row=3, col=1)
    fig.add_hline(y=80, line=dict(color="#ef5350", width=0.6, dash="dash"), row=3, col=1)
    fig.add_hline(y=20, line=dict(color="#26a69a", width=0.6, dash="dash"), row=3, col=1)

    # --- Tầng 4: ADX ---
    fig.add_trace(go.Scatter(x=x, y=d["adx"], name="ADX",
                  line=dict(color="#f5c518", width=1.3)), row=4, col=1)
    fig.add_trace(go.Scatter(x=x, y=d["di_plus"], name="DI+",
                  line=dict(color="#26a69a", width=1)), row=4, col=1)
    fig.add_trace(go.Scatter(x=x, y=d["di_minus"], name="DI-",
                  line=dict(color="#ef5350", width=1)), row=4, col=1)
    fig.add_hline(y=25, line=dict(color="#888", width=0.6, dash="dash"), row=4, col=1)

    fig.update_layout(
        template="plotly_dark", height=height, title=title,
        paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=10, r=70, t=60, b=10), dragmode="pan",
        hovermode="x unified")
    for r in range(1, 5):
        fig.update_xaxes(gridcolor=GRID, row=r, col=1)
        fig.update_yaxes(gridcolor=GRID, row=r, col=1)
    return fig
