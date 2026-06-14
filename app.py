# -*- coding: utf-8 -*-
"""
VN Stock Analyst Desk — bản chạy cloud.
Giá/kỹ thuật/điểm vào: live qua VNDirect dchart.
Chỉ số/BCTC: đọc từ fundamentals.json (máy VN tạo & đẩy lên).
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
import vndirect as VND
import fundamentals as FUND
import ecosystem as ECO
import storage as STORE

st.set_page_config(page_title="VN Stock Analyst Desk", layout="wide", page_icon="📊")
st.markdown("""
<style>
.badge{display:inline-block;padding:3px 10px;border-radius:12px;font-weight:600;font-size:13px}
.b-buy{background:#0a7d2a;color:#fff}.b-hold{background:#b8860b;color:#fff}
.b-sell{background:#c0392b;color:#fff}.b-avoid{background:#7d0a0a;color:#fff}
.small{font-size:12px;color:#888}
</style>""", unsafe_allow_html=True)

st.title("📊 VN Stock Analyst Desk")
st.caption("Giá & điểm vào: live (VNDirect). Chỉ số cơ bản: từ dữ liệu cập nhật định kỳ. "
           "Rule-based, minh bạch. KHÔNG phải khuyến nghị đầu tư cá nhân hóa.")

DISCLAIMER = ("⚠️ Tham khảo, không phải khuyến nghị mua/bán. Nhà đầu tư tự chịu trách nhiệm.")
BAND = {"HOSE": 0.07, "HNX": 0.10, "UPCOM": 0.15}

def rec_badge(label):
    l = label.upper(); cls = "b-hold"
    if "MUA" in l: cls = "b-buy"
    elif "TRÁNH" in l: cls = "b-avoid"
    elif "BÁN" in l: cls = "b-sell"
    return f'<span class="badge {cls}">{label}</span>'

def tradingview_widget(symbol, exchange="HOSE"):
    ex = "HOSE" if exchange.upper() in ("HOSE","HSX") else exchange.upper()
    html = f"""<div class="tradingview-widget-container"><div id="tv_{symbol}"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>new TradingView.widget({{"width":"100%","height":480,
    "symbol":"{ex}:{symbol.upper()}","interval":"D","timezone":"Asia/Ho_Chi_Minh",
    "theme":"dark","style":"1","locale":"vi_VN","allow_symbol_change":false,
    "container_id":"tv_{symbol}"}});</script></div>"""
    st.components.v1.html(html, height=500)

def derive_levels(hist, exchange):
    """Tham chiếu = đóng cửa phiên trước; trần/sàn theo biên độ sàn. (đơn vị nghìn đồng)"""
    ref = VND.ref_from_history(hist)
    if ref is None: return None, None, None
    b = BAND.get(exchange.upper(), 0.07)
    return ref, round(ref*(1+b), 2), round(ref*(1-b), 2)

with st.sidebar:
    st.header("⚙️ Cấu hình")
    universe_name = st.selectbox("Vũ trụ quét", list(U.UNIVERSES.keys()))
    phase = st.selectbox("Giai đoạn vĩ mô (tô đậm ngành hưởng lợi)",
                         list(S.ECONOMIC_PHASES.keys()), index=len(S.ECONOMIC_PHASES)-1)
    period = st.radio("Kỳ BCTC", ["quarter","year"],
                      format_func=lambda x:"Quý" if x=="quarter" else "Năm", horizontal=True)
    source = "VCI"
    st.markdown("**Bộ lọc thanh khoản thị trường**")
    liq_threshold = st.number_input("Ngưỡng HOSE khỏe (tỷ đồng)", value=15000, step=1000)
    avg_price_k = st.number_input("Giá bình quân/cp (nghìn đồng) — chỉnh cho khớp broker",
                                  value=21.0, step=0.5)
    st.markdown("---")
    scan = st.button("🔍 QUÉT THỊ TRƯỜNG", type="primary", use_container_width=True)
    st.caption(f"📅 Chỉ số cơ bản cập nhật: **{FUND.updated_date()}**")
    if not FUND.has_data():
        st.warning("Chưa có file chỉ số (fundamentals.json). Phần giá/điểm vào vẫn chạy. "
                   "Chạy `cap_nhat_co_ban.py` trên máy rồi đẩy lên để có ROE/P/E.")
    st.markdown("---")
    detail_sym = st.text_input("Xem chi tiết 1 mã", value="")
    exchange = st.selectbox("Sàn (biểu đồ & trần/sàn)", ["HOSE","HNX","UPCOM"])

favored = MC.favored_sectors_for_phase(phase)
tab_desk, tab_detail, tab_movers, tab_port, tab_sector = st.tabs(
    ["🖥️ Bảng theo dõi & Điểm vào", "📈 Phân tích chi tiết",
     "📊 Top tăng/giảm", "💼 Sổ mua thử", "🏭 Xu thế ngành"])

with tab_desk:
    st.subheader("🌐 Bối cảnh vĩ mô")
    vi = MC.vnindex_trend(source)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("VN-Index", f"{vi['last']:,.1f}" if vi['last'] else "—",
              f"{vi['chg_1m']:+.1f}% (1T)" if vi['chg_1m'] is not None else None)
    c2.metric("MA50", f"{vi['ma50']:,.1f}" if vi['ma50'] else "—")
    c3.metric("MA200", f"{vi['ma200']:,.1f}" if vi['ma200'] else "—")
    c4.metric("Xu hướng TT", vi['trend'] or "—")
    st.caption(f"Giai đoạn: {phase} · Ngành gió thuận: {', '.join(sorted(favored)) if favored else '—'}")

    # --- Thanh khoản thị trường ---
    liq = MC.hose_liquidity(avg_price_k)
    market_ok = True
    if liq.get("value_ty") is not None:
        market_ok = liq["value_ty"] >= liq_threshold
        icon = "✅ khỏe" if market_ok else "⚠️ yếu"
        l1, l2, l3 = st.columns(3)
        l1.metric("Thanh khoản HOSE (ước)", f"{liq['value_ty']:,.0f} tỷ", icon)
        l2.metric("Khối lượng khớp", f"{liq['vol_shares']/1e6:,.0f} tr cp" if liq['vol_shares'] else "—")
        l3.metric("So TB 20 phiên", f"{liq['vs_avg20_pct']:,.0f}%" if liq['vs_avg20_pct'] else "—")
        if not market_ok:
            st.warning(f"Thanh khoản HOSE ~{liq['value_ty']:,.0f} tỷ < ngưỡng {liq_threshold:,.0f} tỷ "
                       "→ thị trường yếu, mọi tín hiệu ĐIỂM VÀO bị hạ xuống CHỜ.")
    else:
        st.caption(f"(Chưa tính được thanh khoản: {liq.get('err','')})")
    st.divider()

    st.subheader("🖥️ Danh sách theo dõi & trạng thái điểm vào")
    if scan:
        symbols = U.UNIVERSES[universe_name]
        prog = st.progress(0.0, text="Bắt đầu quét…")
        def cb(p, sym): prog.progress(p, text=f"Đang quét {sym} ({int(p*100)}%)")
        rows = SC.run_screen(symbols, period, source, favored, progress_cb=cb)
        rows = SC.apply_market_filter(rows, market_ok)
        prog.empty()
        st.session_state["scan_rows"] = rows

    rows = st.session_state.get("scan_rows")
    if rows:
        df = pd.DataFrame(rows)
        only = st.multiselect("Lọc trạng thái",
            ["🟢 ĐIỂM VÀO","🟡 CHỜ ĐIỂM VÀO","🔵 THEO DÕI","🔴 TRÁNH"],
            default=["🟢 ĐIỂM VÀO","🟡 CHỜ ĐIỂM VÀO"])
        view = df[df["Trạng thái"].isin(only)] if only else df
        cols = [c for c in ["Mã","Trạng thái","Vùng","Vùng chờ","Ngành","Gió ngành","Điểm CB","Xu hướng",
                "RSI","%1M","%3M","%6M","%YTD","P/E","ROE%","Cảnh báo","Giá","Setup"] if c in view.columns]
        st.dataframe(view[cols], hide_index=True, use_container_width=True, height=520)
        n_vao=(df["status"]=="VAO").sum(); n_cho=(df["status"]=="CHO").sum()
        st.success(f"🟢 {n_vao} mã ĐIỂM VÀO · 🟡 {n_cho} mã CHỜ (tổng {len(df)} mã).")

        # --- Lưu & xuất báo cáo ---
        bC1, bC2, bC3 = st.columns(3)
        csv = view[cols].to_csv(index=False).encode("utf-8-sig")
        bC1.download_button("⬇️ Tải CSV (mở Excel)", csv,
                            file_name=f"quet_thi_truong_{datetime.now():%Y%m%d_%H%M}.csv",
                            mime="text/csv", use_container_width=True)
        if bC2.button("💾 Lưu phiên quét này", use_container_width=True):
            ok = STORE.save_scan(rows, meta={"phase": phase, "liq": liq.get("value_ty")})
            st.toast("Đã lưu phiên quét." if ok else "Lưu thất bại.", icon="✅" if ok else "⚠️")
        saved = STORE.load_scan()
        if saved:
            bC3.caption(f"📁 Phiên đã lưu: {saved.get('_saved','')}")

        st.caption("Xếp hạng: VÀO trước → gió ngành thuận → điểm cơ bản cao. " + DISCLAIMER)
        errs=[r for r in rows if r.get("_err")]
        if errs:
            with st.expander(f"⚠ {len(errs)} mã lỗi dữ liệu"):
                for r in errs: st.write(f"• {r['Mã']}: {r['_err'][0]}")
    else:
        st.info("Bấm **QUÉT THỊ TRƯỜNG** để app tự lập danh sách & báo điểm vào.")

with tab_detail:
    sym = (detail_sym or "").strip().upper()
    if not sym:
        st.info("Nhập 1 mã ở ô **'Xem chi tiết 1 mã'** (thanh bên).")
    else:
        st.markdown(f"## {sym}")
        with st.spinner(f"Phân tích {sym}…"):
            end=datetime.now().strftime("%Y-%m-%d")
            start=(datetime.now()-timedelta(days=400)).strftime("%Y-%m-%d")
            hist,_=D.get_price_history(sym,start,end,"1D",source)
            ratio,_=D.get_ratios(sym,period,source)
            cur,_=A.extract_metrics(ratio)
            if not cur or all(v is None for v in cur.values()):
                cur=FUND.get_metrics(sym)
            growth=FUND.get_growth(sym); cf=FUND.get_cashflow(sym)
            warns=A.detect_warnings(cur,growth,cf)
            sc=A.score_stock(cur,growth,cf)
            label,conf=A.recommendation(sc["total"],warns)
            status=MK.candle_status(hist)
            setup=MK.entry_setup(hist)
            ref,ceil,floor=derive_levels(hist,exchange)

        a,b,c,d=st.columns([2,1,1,1])
        a.markdown("**Khuyến nghị:** "+rec_badge(label)+
                   f" <span class='small'>(tin cậy {conf} · {sc['total']}/100)</span>",unsafe_allow_html=True)
        b.metric("Tham chiếu", f"{ref:,.2f}" if ref else "—")
        c.metric("Trần 🔴", f"{ceil:,.2f}" if ceil else "—")
        d.metric("Sàn 🔵", f"{floor:,.2f}" if floor else "—")
        st.caption("Giá đơn vị nghìn đồng (theo VNDirect). Tham chiếu = đóng cửa phiên trước.")

        st.markdown("**🎯 Điểm vào lệnh:** "+SC.STATUS_LABEL.get(setup["status"],"—"))
        wz = setup.get("wait_zone")
        if wz:
            za = setup.get("zone_alert", "")
            st.markdown(f"**📍 Vùng chờ vào: `{wz['low']:,.2f} – {wz['high']:,.2f}`** "
                        f"({' + '.join(wz['factors'])}) {za}")
        for r in setup["reasons"]: st.write("•", r)
        if setup.get("adx_text"):
            st.caption("📊 " + setup["adx_text"])
        if setup.get("confluence"):
            st.markdown("**🔬 Xác nhận đa chỉ báo (MACD 24-52-14 · Stoch 42-5-3 · ADX · Fibonacci):**")
            for cf in setup["confluence"]: st.write("  ▸", cf)
        st.info(f"**Trạng thái nến:** {status['summary']}")
        with st.expander("Tín hiệu kỹ thuật chi tiết"):
            for s in status["signals"]: st.write("•", s)

        # --- Biểu đồ Plotly đa tầng (giống app vàng) ---
        try:
            import indicators as IND
            import charts as CH
            cc1, cc2 = st.columns([1, 3])
            with cc1:
                tf = st.radio("Khung", ["Ngày (D1)", "Tuần (W1)"], horizontal=False)
            with cc2:
                st.caption("Bật/tắt chỉ báo:")
                tg1, tg2, tg3, tg4, tg5 = st.columns(5)
                show_ema = tg1.checkbox("EMA", value=True)
                show_macd = tg2.checkbox("MACD", value=True)
                show_stoch = tg3.checkbox("Stoch", value=True)
                show_adx = tg4.checkbox("ADX", value=True)
                show_fib = tg5.checkbox("Fibo", value=True)

            src = IND.weekly_resample(hist) if tf.startswith("Tuần") else hist
            d_ind = IND.add_indicators(src)
            fib = IND.fibonacci_levels(src, lookback=120) if show_fib else None
            wz_chart = setup.get("wait_zone")
            fig = CH.build_chart(d_ind, fib, title=f"{sym} — {tf}",
                                 show_ema=show_ema, show_macd=show_macd,
                                 show_stoch=show_stoch, show_adx=show_adx,
                                 wait_zone=wz_chart)
            st.plotly_chart(fig, use_container_width=True,
                            config={"scrollZoom": True, "displayModeBar": True,
                                    "responsive": True})
            st.caption("📊 Biểu đồ trên là **giá chuẩn (VNDirect)** — mọi phân tích/điểm vào dựa trên dữ liệu này. "
                       "Đường gạch trắng = giá hiện tại, dải xanh = vùng chờ.")
        except Exception as e:
            st.caption(f"(Chưa vẽ được biểu đồ: {type(e).__name__}: {e})")

        with st.expander("📉 Biểu đồ TradingView (phụ — khóa mã HOSE)"):
            st.caption("⚠️ TradingView chỉ để tham khảo. Nếu hiện sai mã (trùng tên với cổ phiếu nước ngoài), "
                       "hãy tin biểu đồ Plotly ở trên.")
            tradingview_widget(sym, exchange)

        if not cur or all(v is None for v in (cur or {}).values()):
            st.warning("Chưa có chỉ số cơ bản cho mã này (cần cập nhật fundamentals.json từ máy). "
                       "Phần kỹ thuật/điểm vào ở trên vẫn chính xác.")
        else:
            st.markdown("**Điểm 4 trụ (mỗi trụ ≤25):**")
            pc=st.columns(4)
            nmap={"profitability":"Sinh lời","health":"Sức khỏe TC","growth":"Tăng trưởng","valuation":"Định giá"}
            for col,(k,nm) in zip(pc,nmap.items()): col.metric(nm,f"{sc['pillars'].get(k,0)}/25")
            def fmt(v,s=""): return f"{v:,.2f}{s}" if isinstance(v,(int,float)) else "—"
            g=growth
            tbl={"ROE":fmt(cur.get('roe'),'%'),"ROA":fmt(cur.get('roa'),'%'),
                 "Biên gộp":fmt(cur.get('gross_margin'),'%'),"Biên ròng":fmt(cur.get('net_margin'),'%'),
                 "P/E":fmt(cur.get('pe')),"P/B":fmt(cur.get('pb')),"Nợ/VCSH":fmt(cur.get('de')),
                 "DT YoY":fmt(g.get('rev_yoy'),'%'),"LNST YoY":fmt(g.get('npat_yoy'),'%')}
            st.dataframe(pd.DataFrame(tbl.items(),columns=["Chỉ số","Giá trị"]),
                         hide_index=True,use_container_width=True)
            L,R=st.columns(2)
            with L:
                st.markdown("**✅ Luận điểm/Điểm mạnh:**")
                for cat,items in sc["reasons"].items():
                    for it in items:
                        if not it.startswith("⚠"): st.write("•",it)
            with R:
                st.markdown("**⚠️ Cảnh báo:**")
                if warns:
                    for w in warns:
                        ic="🔴" if w["level"]=="high" else "🟠" if w["level"]=="medium" else "🟡"
                        st.write(ic,w["msg"])
                else: st.write("Không có cảnh báo nghiêm trọng.")
        # --- NHẬN ĐỊNH TỔNG HỢP ---
        st.markdown("---")
        st.markdown("### 🧭 Nhận định tổng hợp")
        eco_name, eco_desc = ECO.get_ecosystem(sym)
        div = FUND.get_dividend(sym)

        cN1, cN2 = st.columns(2)
        with cN1:
            st.markdown("**🏛️ Nền tảng & hệ sinh thái**")
            if eco_name:
                st.write(f"• Hệ **{eco_name}**: {eco_desc}")
            else:
                st.write("• Chưa gắn hệ sinh thái (bổ sung trong ecosystem.py).")
            if cur and any(v is not None for v in (cur or {}).values()):
                roe = cur.get("roe"); de = cur.get("de")
                if roe is not None:
                    tag = "khỏe" if roe >= 15 else "trung bình" if roe >= 8 else "yếu"
                    st.write(f"• Sinh lời: ROE {roe:.1f}% ({tag})")
                if de is not None:
                    tag = "an toàn" if de <= 0.7 else "chấp nhận" if de <= 1.5 else "đòn bẩy cao"
                    st.write(f"• Tài chính: Nợ/VCSH {de:.2f} ({tag})")
            else:
                st.write("• Chỉ số cơ bản: chưa có (chạy cập nhật).")
        with cN2:
            st.markdown("**💰 Cổ tức / sự kiện**")
            if div:
                st.write(f"• Mới nhất ({div.get('ngay','')}): {div.get('moi','')}")
                for ln in div.get("lines", [])[1:3]:
                    st.write(f"  – {ln['ngay']}: {ln['noi_dung']}")
            else:
                st.write("• Chưa có dữ liệu cổ tức (chạy cập nhật trên máy).")

        st.markdown("**📈 Triển vọng & dự báo kỹ thuật:**")
        prospect = []
        if setup.get("trend"): prospect.append(f"Xu hướng {setup['trend'].lower()}")
        if setup.get("adx_text"): prospect.append(setup["adx_text"])
        if wz:
            za = setup.get("zone_alert","")
            prospect.append(f"Vùng canh vào {wz['low']:,.2f}–{wz['high']:,.2f} {za}")
        st.write("• " + " · ".join(prospect) if prospect else "• Chưa đủ dữ liệu.")
        st.write(f"• **Kết luận:** {rec_badge(label)} (điểm {sc['total']}/100, tin cậy {conf})",
                 unsafe_allow_html=True)

        st.caption(DISCLAIMER)

with tab_movers:
    st.subheader("📊 Top tăng / giảm theo thời gian")
    st.caption("Lọc nhóm mã GIẢM sâu để soi điểm vào (bắt đáy/canh pullback), "
               "hoặc xem nhóm TĂNG mạnh để tránh đu đỉnh. Dữ liệu giá VNDirect.")
    rows_m = st.session_state.get("scan_rows")
    if not rows_m:
        st.info("Bấm **QUÉT THỊ TRƯỜNG** ở tab đầu để có dữ liệu thống kê.")
    else:
        import pandas as _pd
        dfm = _pd.DataFrame(rows_m)
        period = st.radio("Mốc thời gian", ["%1M","%3M","%6M","%YTD"],
                          format_func=lambda x: {"%1M":"1 tháng","%3M":"3 tháng",
                          "%6M":"6 tháng","%YTD":"Từ đầu năm"}[x], horizontal=True)
        if period in dfm.columns:
            valid = dfm[dfm[period].notna()].copy()
            valid[period] = _pd.to_numeric(valid[period], errors="coerce")
            valid = valid.dropna(subset=[period])
            show_cols = [c for c in ["Mã","Ngành","Trạng thái",period,"Vùng chờ","RSI","Giá"] if c in valid.columns]
            up = valid.sort_values(period, ascending=False).head(15)
            down = valid.sort_values(period, ascending=True).head(15)
            n_up = (valid[period] > 0).sum(); n_down = (valid[period] < 0).sum()
            m1, m2 = st.columns(2)
            m1.metric(f"Số mã TĂNG ({period[1:]})", f"{n_up} mã")
            m2.metric(f"Số mã GIẢM ({period[1:]})", f"{n_down} mã")
            cU, cD = st.columns(2)
            with cU:
                st.markdown(f"**🔺 Top tăng mạnh ({period[1:]}) — cân nhắc tránh đu đỉnh**")
                st.dataframe(up[show_cols], use_container_width=True, hide_index=True)
            with cD:
                st.markdown(f"**🔻 Top giảm sâu ({period[1:]}) — soi tìm điểm vào**")
                st.dataframe(down[show_cols], use_container_width=True, hide_index=True)
        else:
            st.warning("Chưa có dữ liệu mốc này. Quét lại thị trường.")

with tab_port:
    st.subheader("💼 Sổ mua thử (test phương pháp)")
    st.caption("Đánh dấu mã đã 'mua thử' — app lưu giá & ngày vào, lần sau tự tính lời/lỗ. "
               "Test phương pháp như thật mà không mất tiền. (Lưu vào portfolio.json — tải về & push để giữ lâu.)")

    # form thêm vị thế
    with st.expander("➕ Thêm lệnh mua thử"):
        f1, f2, f3, f4 = st.columns(4)
        p_sym = f1.text_input("Mã", "").strip().upper()
        p_price = f2.number_input("Giá mua (nghìn đồng)", min_value=0.0, value=0.0, step=0.1)
        p_qty = f3.number_input("Số lượng (cp)", min_value=0, value=100, step=100)
        p_note = f4.text_input("Ghi chú", "")
        if st.button("Lưu lệnh mua thử"):
            if p_sym and p_price > 0:
                STORE.add_position(p_sym, p_price, p_qty, p_note)
                st.toast(f"Đã thêm {p_sym} @ {p_price}", icon="✅")
                st.rerun()
            else:
                st.warning("Nhập mã và giá mua hợp lệ.")

    positions = STORE.load_portfolio()
    if not positions:
        st.info("Chưa có lệnh mua thử nào. Thêm ở mục trên.")
    else:
        # lấy giá hiện tại cho từng mã
        cur_prices = {}
        for p in positions:
            try:
                h = VND.vnd_history(p["sym"],
                    (datetime.now()).strftime("%Y-%m-%d"), None) if False else None
            except Exception:
                h = None
        # dùng giá từ phiên quét nếu có, else fetch nhanh
        scan_rows = st.session_state.get("scan_rows") or []
        price_map = {r["Mã"]: r.get("Giá") for r in scan_rows if r.get("Giá")}
        for p in positions:
            cur_prices[p["sym"]] = price_map.get(p["sym"])
        # mã nào chưa có giá -> fetch
        for p in positions:
            if cur_prices.get(p["sym"]) is None:
                try:
                    px = VND.last_price(p["sym"])
                    cur_prices[p["sym"]] = px
                except Exception:
                    pass

        enriched, summary = STORE.compute_pnl(positions, cur_prices)

        # --- Dashboard tổng quan ---
        d1, d2, d3 = st.columns(3)
        d1.metric("Tổng vốn (nghìn đ)", f"{summary['total_cost']:,.0f}")
        d2.metric("Giá trị hiện tại", f"{summary['total_value']:,.0f}")
        d3.metric("Lời/Lỗ", f"{summary['total_pnl']:,.0f}",
                  f"{summary['total_pnl_pct']:+.1f}%")

        import pandas as _pd
        dfp = _pd.DataFrame(enriched)
        # biểu đồ lời/lỗ theo mã
        try:
            import plotly.graph_objects as go
            valid = dfp[dfp["pnl_pct"].notna()]
            if not valid.empty:
                colors = ["#26a69a" if v >= 0 else "#ef5350" for v in valid["pnl_pct"]]
                fig = go.Figure(go.Bar(x=valid["sym"], y=valid["pnl_pct"],
                                marker_color=colors,
                                text=[f"{v:+.1f}%" for v in valid["pnl_pct"]],
                                textposition="outside"))
                fig.update_layout(template="plotly_dark", height=300,
                    title="Lời/Lỗ theo mã (%)", paper_bgcolor="#0e1117",
                    plot_bgcolor="#0e1117", margin=dict(l=10,r=10,t=40,b=10),
                    yaxis_title="%")
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

        # bảng chi tiết
        show = dfp.rename(columns={"sym":"Mã","entry":"Giá mua","current":"Giá hiện tại",
                "qty":"SL","pnl_pct":"Lời/Lỗ %","pnl_value":"Lời/Lỗ (ngđ)",
                "date":"Ngày mua","note":"Ghi chú"})
        show_cols = [c for c in ["Mã","Ngày mua","Giá mua","Giá hiện tại","SL",
                     "Lời/Lỗ %","Lời/Lỗ (ngđ)","Ghi chú"] if c in show.columns]
        st.dataframe(show[show_cols], hide_index=True, use_container_width=True)

        # xuất + xóa
        e1, e2 = st.columns(2)
        csv_p = show[show_cols].to_csv(index=False).encode("utf-8-sig")
        e1.download_button("⬇️ Tải sổ mua thử (CSV)", csv_p,
                           file_name=f"so_mua_thu_{datetime.now():%Y%m%d}.csv",
                           mime="text/csv", use_container_width=True)
        idx_del = e2.number_input("Xóa lệnh số (1-based)", min_value=0,
                                  max_value=len(positions), value=0)
        if e2.button("Xóa lệnh") and idx_del > 0:
            STORE.remove_position(idx_del - 1)
            st.rerun()
        st.caption(DISCLAIMER)

with tab_sector:
    st.subheader("🏭 Xu thế ngành theo giai đoạn kinh tế")
    info=S.ECONOMIC_PHASES[phase]
    st.write(f"**Giai đoạn:** {phase}"); st.write(f"**Bối cảnh:** {info['mo_ta']}")
    A1,B1=st.columns(2)
    with A1:
        st.markdown("### 🟢 Nhóm hưởng lợi")
        for nm,why in info["huong_loi"]:
            st.markdown(f"**{nm}**  \n<span class='small'>{why}</span>",unsafe_allow_html=True)
    with B1:
        st.markdown("### 🔴 Nhóm bất lợi")
        for nm,why in info["bat_loi"]:
            st.markdown(f"**{nm}**  \n<span class='small'>{why}</span>",unsafe_allow_html=True)
    st.divider()
    sec=st.selectbox("Cổ phiếu tiêu biểu theo ngành", list(S.SECTOR_TICKERS.keys()))
    st.write(", ".join(S.SECTOR_TICKERS[sec]))
    st.caption("Danh mục tham khảo, KHÔNG phải khuyến nghị.")
