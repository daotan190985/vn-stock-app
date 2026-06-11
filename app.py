# -*- coding: utf-8 -*-
"""
VN Stock Fundamental Analyzer — Bàn làm việc của Analyst
Mở app là có ngay: bối cảnh vĩ mô + danh sách mã theo dõi + trạng thái điểm vào.

Chạy: streamlit run app.py
"""
import warnings; warnings.filterwarnings("ignore")
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

import data as D
import analyzer as A
import market as MK
import sectors as S
import universe as U
import screener as SC
import macro as MC

st.set_page_config(page_title="VN Stock Analyst Desk", layout="wide", page_icon="📊")

st.markdown("""
<style>
.badge{display:inline-block;padding:3px 10px;border-radius:12px;font-weight:600;font-size:13px}
.b-buy{background:#0a7d2a;color:#fff}.b-hold{background:#b8860b;color:#fff}
.b-sell{background:#c0392b;color:#fff}.b-avoid{background:#7d0a0a;color:#fff}
.small{font-size:12px;color:#888}
</style>
""", unsafe_allow_html=True)

st.title("📊 VN Stock Analyst Desk")
st.caption("Bàn làm việc analyst: vĩ mô → bảng theo dõi → điểm vào → phân tích cơ bản chuyên sâu. "
           "Rule-based, minh bạch. KHÔNG phải khuyến nghị đầu tư cá nhân hóa.")

# --- Tự động kiểm tra & cài thư viện dữ liệu nếu thiếu ---
def _ensure_package(pkg, import_name=None):
    """Thử import; nếu thiếu thì tự pip install rồi import lại."""
    import importlib, subprocess, sys
    name = import_name or pkg
    try:
        importlib.import_module(name)
        return True
    except Exception:
        st.warning(f"⏳ Thiếu thư viện `{pkg}` — app đang TỰ CÀI lần đầu, vui lòng chờ 1–3 phút "
                   f"(không tắt cửa sổ).")
        with st.spinner(f"Đang cài {pkg}…"):
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            except Exception as e:
                st.error(f"❌ Không tự cài được `{pkg}` ({e}).\n\n"
                         f"Hãy mở PowerShell gõ thủ công: `pip install {pkg}` rồi chạy lại app.")
                st.stop()
        importlib.invalidate_caches()
        try:
            importlib.import_module(name)
            st.success(f"✅ Đã cài xong `{pkg}`.")
            return True
        except Exception:
            st.info(f"✅ Đã cài `{pkg}`. Hãy **tắt app và mở lại** để áp dụng.")
            if st.button("🔄 Tải lại app"):
                st.rerun()
            st.stop()

_ensure_package("vnstock")

DISCLAIMER = ("⚠️ Nội dung tham khảo dựa trên dữ liệu vnstock (có thể trễ/thiếu). "
              "Không phải khuyến nghị mua/bán. Nhà đầu tư tự chịu trách nhiệm.")

def rec_badge(label):
    l = label.upper(); cls = "b-hold"
    if "MUA" in l: cls = "b-buy"
    elif "TRÁNH" in l: cls = "b-avoid"
    elif "BÁN" in l: cls = "b-sell"
    return f'<span class="badge {cls}">{label}</span>'

def tradingview_widget(symbol, exchange="HOSE"):
    ex = "HOSE" if exchange.upper() in ("HOSE","HSX") else exchange.upper()
    html = f"""
    <div class="tradingview-widget-container"><div id="tv_{symbol}"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>new TradingView.widget({{"width":"100%","height":480,
    "symbol":"{ex}:{symbol.upper()}","interval":"D","timezone":"Asia/Ho_Chi_Minh",
    "theme":"dark","style":"1","locale":"vi_VN","toolbar_bg":"#1e1e1e",
    "hide_side_toolbar":false,"allow_symbol_change":true,"container_id":"tv_{symbol}"}});</script></div>"""
    st.components.v1.html(html, height=500)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("⚙️ Cấu hình")
    universe_name = st.selectbox("Vũ trụ quét", list(U.UNIVERSES.keys()))
    period = st.radio("Kỳ BCTC", ["quarter","year"],
                      format_func=lambda x:"Quý" if x=="quarter" else "Năm", horizontal=True)
    source = st.selectbox("Nguồn", ["VCI","KBS"])
    st.markdown("**Giai đoạn vĩ mô hiện tại**")
    phase = st.selectbox("Chọn giai đoạn (tô đậm ngành hưởng lợi)", list(S.ECONOMIC_PHASES.keys()),
                         index=len(S.ECONOMIC_PHASES)-1)
    st.markdown("---")
    scan = st.button("🔍 QUÉT THỊ TRƯỜNG", type="primary", use_container_width=True)
    st.caption("Lần quét đầu hơi lâu (mỗi mã vài giây). Kết quả cache 1 giờ.")
    st.markdown("---")
    detail_sym = st.text_input("Xem chi tiết 1 mã", value="")
    exchange = st.selectbox("Sàn (biểu đồ & trần/sàn)", ["HOSE","HNX","UPCOM"])

favored = MC.favored_sectors_for_phase(phase)

tab_desk, tab_detail, tab_sector = st.tabs(
    ["🖥️ Bảng theo dõi & Điểm vào", "📈 Phân tích chi tiết", "🏭 Xu thế ngành"])

# ============ TAB 1: BÀN LÀM VIỆC ============
with tab_desk:
    # --- Panel vĩ mô ---
    st.subheader("🌐 Bối cảnh vĩ mô")
    vi = MC.vnindex_trend(source)
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("VN-Index", f"{vi['last']:,.1f}" if vi['last'] else "—",
               f"{vi['chg_1m']:+.1f}% (1 tháng)" if vi['chg_1m'] is not None else None)
    mc2.metric("MA50", f"{vi['ma50']:,.1f}" if vi['ma50'] else "—")
    mc3.metric("MA200", f"{vi['ma200']:,.1f}" if vi['ma200'] else "—")
    mc4.metric("Xu hướng TT", vi['trend'] or "—")
    st.markdown(f"**Giai đoạn đang chọn:** {phase}")
    st.caption(f"Ngành được tô đậm (gió thuận): {', '.join(sorted(favored)) if favored else 'không có'}")
    if vi.get("err"):
        st.caption(f"({vi['err']})")
    st.divider()

    # --- Bảng quét ---
    st.subheader("🖥️ Danh sách theo dõi & trạng thái điểm vào")
    if scan:
        symbols = U.UNIVERSES[universe_name]
        prog = st.progress(0.0, text="Bắt đầu quét…")
        def cb(p, sym): prog.progress(p, text=f"Đang quét {sym} ({int(p*100)}%)")
        rows = SC.run_screen(symbols, period, source, favored, progress_cb=cb)
        prog.empty()
        st.session_state["scan_rows"] = rows

    rows = st.session_state.get("scan_rows")
    if rows:
        df = pd.DataFrame(rows)
        # bộ lọc nhanh
        f1, f2 = st.columns([1,3])
        with f1:
            only = st.multiselect("Lọc trạng thái",
                ["🟢 ĐIỂM VÀO","🟡 CHỜ ĐIỂM VÀO","🔵 THEO DÕI","🔴 TRÁNH"],
                default=["🟢 ĐIỂM VÀO","🟡 CHỜ ĐIỂM VÀO"])
        view = df[df["Trạng thái"].isin(only)] if only else df
        show_cols = ["Mã","Trạng thái","Ngành","Gió ngành","Điểm CB","Xu hướng",
                     "RSI","P/E","ROE%","Cảnh báo","Giá","Setup"]
        show_cols = [c for c in show_cols if c in view.columns]
        st.dataframe(view[show_cols], hide_index=True, use_container_width=True, height=520)

        # tóm tắt
        n_vao = (df["status"]=="VAO").sum(); n_cho = (df["status"]=="CHO").sum()
        st.success(f"🟢 {n_vao} mã đang ở ĐIỂM VÀO · 🟡 {n_cho} mã đang CHỜ điểm vào "
                   f"(trong tổng {len(df)} mã quét).")
        st.caption("Sắp xếp: trạng thái vào trước → gió ngành thuận → điểm cơ bản cao. " + DISCLAIMER)

        errs = [r for r in rows if r.get("_err")]
        if errs:
            with st.expander(f"⚠ {len(errs)} mã lỗi dữ liệu"):
                for r in errs: st.write(f"• {r['Mã']}: {r['_err'][0]}")
    else:
        st.info("Bấm **QUÉT THỊ TRƯỜNG** ở thanh bên để app tự lập danh sách theo dõi và báo điểm vào.")

# ============ TAB 2: CHI TIẾT 1 MÃ ============
with tab_detail:
    sym = (detail_sym or "").strip().upper()
    if not sym:
        st.info("Nhập 1 mã ở ô **'Xem chi tiết 1 mã'** (thanh bên) để xem báo cáo đầy đủ.")
    else:
        st.markdown(f"## {sym}")
        with st.spinner(f"Phân tích {sym}…"):
            ratio,_ = D.get_ratios(sym,period,source)
            income,_ = D.get_income(sym,period,source)
            cashf,_ = D.get_cashflow(sym,period,source)
            cur,_ = A.extract_metrics(ratio)
            growth = A.compute_growth(income)
            cf = A.analyze_cashflow(cashf)
            warns = A.detect_warnings(cur,growth,cf)
            sc = A.score_stock(cur,growth,cf)
            label,conf = A.recommendation(sc["total"],warns)

            board_df,_ = D.get_price_board(sym,source)
            board = MK.parse_price_board(board_df,exchange)
            end = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now()-timedelta(days=400)).strftime("%Y-%m-%d")
            hist,_ = D.get_price_history(sym,start,end,"1D",source)
            status = MK.candle_status(hist,board)
            setup = MK.entry_setup(hist,board)

        c1,c2,c3,c4 = st.columns([2,1,1,1])
        c1.markdown("**Khuyến nghị:** "+rec_badge(label)+
                    f" <span class='small'>(tin cậy {conf} · {sc['total']}/100)</span>",unsafe_allow_html=True)
        c2.metric("Tham chiếu", f"{board['ref']:,.0f}" if board['ref'] else "—")
        c3.metric("Trần 🔴", f"{board['ceil']:,.0f}" if board['ceil'] else "—")
        c4.metric("Sàn 🔵", f"{board['floor']:,.0f}" if board['floor'] else "—")

        st.markdown("**🎯 Điểm vào lệnh:** "+SC.STATUS_LABEL.get(setup["status"],"—"))
        for r in setup["reasons"]: st.write("•", r)
        st.info(f"**Trạng thái nến:** {status['summary']}")
        with st.expander("Tín hiệu kỹ thuật chi tiet"):
            for s in status["signals"]: st.write("•", s)
        with st.expander("📉 Biểu đồ nến TradingView (Daily)"):
            tradingview_widget(sym, exchange)

        st.markdown("**Điểm 4 trụ (mỗi trụ ≤25):**")
        pc = st.columns(4)
        nmap = {"profitability":"Sinh lời","health":"Sức khỏe TC","growth":"Tăng trưởng","valuation":"Định giá"}
        for col,(k,nm) in zip(pc,nmap.items()): col.metric(nm,f"{sc['pillars'].get(k,0)}/25")

        def fmt(v,suf=""): return f"{v:,.2f}{suf}" if isinstance(v,(int,float)) else "—"
        g=growth
        rows={"ROE":fmt(cur.get('roe'),'%'),"ROA":fmt(cur.get('roa'),'%'),
              "Biên gộp":fmt(cur.get('gross_margin'),'%'),"Biên ròng":fmt(cur.get('net_margin'),'%'),
              "P/E":fmt(cur.get('pe')),"P/B":fmt(cur.get('pb')),"Nợ/VCSH":fmt(cur.get('de')),
              "Thanh toán HH":fmt(cur.get('current_ratio')),"DT YoY":fmt(g.get('rev_yoy'),'%'),
              "LNST YoY":fmt(g.get('npat_yoy'),'%'),"CFO":fmt(cf.get('cfo_latest'))}
        st.dataframe(pd.DataFrame(rows.items(),columns=["Chỉ số","Giá trị"]),
                     hide_index=True,use_container_width=True)

        cL,cR = st.columns(2)
        with cL:
            st.markdown("**✅ Luận điểm/Điểm mạnh:**")
            for cat,items in sc["reasons"].items():
                for it in items:
                    if not it.startswith("⚠"): st.write("•",it)
        with cR:
            st.markdown("**⚠️ Cảnh báo rủi ro:**")
            if warns:
                for w in warns:
                    ic = "🔴" if w["level"]=="high" else "🟠" if w["level"]=="medium" else "🟡"
                    st.write(ic,w["msg"])
            else: st.write("Không có cảnh báo nghiêm trọng.")
        st.caption(DISCLAIMER)

# ============ TAB 3: XU THẾ NGÀNH ============
with tab_sector:
    st.subheader("🏭 Xu thế ngành theo giai đoạn kinh tế")
    info = S.ECONOMIC_PHASES[phase]
    st.write(f"**Giai đoạn:** {phase}")
    st.write(f"**Bối cảnh:** {info['mo_ta']}")
    cA,cB = st.columns(2)
    with cA:
        st.markdown("### 🟢 Nhóm hưởng lợi")
        for name,why in info["huong_loi"]:
            st.markdown(f"**{name}**  \n<span class='small'>{why}</span>",unsafe_allow_html=True)
    with cB:
        st.markdown("### 🔴 Nhóm bất lợi")
        for name,why in info["bat_loi"]:
            st.markdown(f"**{name}**  \n<span class='small'>{why}</span>",unsafe_allow_html=True)
    st.divider()
    sec = st.selectbox("Cổ phiếu tiêu biểu theo ngành", list(S.SECTOR_TICKERS.keys()))
    st.write(", ".join(S.SECTOR_TICKERS[sec]))
    st.caption("Danh mục tham khảo, KHÔNG phải khuyến nghị.")
