# -*- coding: utf-8 -*-
"""
CAP NHAT DU LIEU CO BAN — chay tren MAY VN (Python co vnstock).
Lay: chi so tai chinh (vnstock) + co tuc (Vietstock) cho ~70 ma.
Tao file fundamentals.json de cloud doc.

CHAY (dung python co vnstock, vi du Python 3.11):
    python cap_nhat_co_ban.py
Sau do day len GitHub (git add/commit/push hoac DAY_LEN.bat).
Chi can chay MOI QUY 1 LAN (hoac khi muon cap nhat co tuc).
"""
import warnings; warnings.filterwarnings("ignore")
import json, time, re
from io import StringIO
from datetime import datetime
import requests

VN30 = ["ACB","BCM","BID","BVH","CTG","FPT","GAS","GVR","HDB","HPG",
        "MBB","MSN","MWG","PLX","POW","SAB","SHB","SSB","SSI","STB",
        "TCB","TPB","VCB","VHM","VIB","VIC","VJC","VNM","VPB","VRE"]
MIDCAP = ["DGC","DCM","DPM","KDH","NLG","PDR","DXG","KBC","IDC","SZC",
          "VGC","HSG","NKG","PNJ","FRT","DGW","REE","NT2","PC1","GMD",
          "HAH","VSC","PVT","PVS","PVD","BSR","DHG","IMP","VCI","VND",
          "HCM","CTD","HHV","VCG","GEX","DBC","ANV","VHC","FTS","CMG"]
SYMBOLS = VN30 + MIDCAP

_H = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0 Safari/537.36",
      "Accept":"text/html,application/xhtml+xml,*/*;q=0.8",
      "Referer":"https://finance.vietstock.vn/"}


def get_ratios_vnstock(sym):
    """Chi so tai chinh tu vnstock. Tra dict hoac {}."""
    try:
        from vnstock import Vnstock
        st = Vnstock().stock(symbol=sym, source="VCI")
        df = st.finance.ratio(period="quarter", lang="en", dropna=False)
        if df is None or df.empty:
            return {}
        row = df.iloc[-1]
        cols = {(" ".join(map(str,c)) if isinstance(c,tuple) else str(c)).lower(): c
                for c in df.columns}
        def g(*cands):
            for cand in cands:
                for k,o in cols.items():
                    if cand in k:
                        try:
                            v = float(row[o])
                            return round(v,2)
                        except: pass
            return None
        out = {"roe":g("roe"),"roa":g("roa"),
               "pe":g("p/e","pe"),"pb":g("p/b","pb"),
               "net_margin":g("net profit margin","post-tax"),
               "gross_margin":g("gross profit margin","gross margin"),
               "de":g("debt/equity","debt to equity","liabilities/equity"),
               "current_ratio":g("current ratio")}
        # roe/roa/margin co the la ti le -> %
        for k in ("roe","roa","net_margin","gross_margin"):
            if out.get(k) is not None and abs(out[k]) < 5:
                out[k] = round(out[k]*100,2)
        return {k:v for k,v in out.items() if v is not None}
    except Exception as e:
        return {}


def get_dividend_vietstock(sym):
    """Co tuc moi nhat tu Vietstock (read_html). Tra dict hoac {}."""
    try:
        import pandas as pd
        from bs4 import BeautifulSoup
        url = f"https://finance.vietstock.vn/{sym}/co-tuc.htm"
        r = requests.get(url, headers=_H, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", class_=lambda x: x and "table" in x)
        if not table:
            return {}
        df = pd.read_html(StringIO(str(table)))[0]
        if df.empty:
            return {}
        lines = []
        for _, rr in df.head(5).iterrows():
            d = str(rr.iloc[0]).strip()
            c = str(rr.iloc[1]).strip() if len(rr) > 1 else ""
            if c and c != "nan":
                lines.append({"ngay": d, "noi_dung": c[:160]})
        if not lines:
            return {}
        return {"co_tuc_moi": lines[0]["noi_dung"], "co_tuc_ngay": lines[0]["ngay"],
                "co_tuc_lines": lines}
    except Exception:
        return {}


def main():
    result = {"_updated": datetime.now().strftime("%Y-%m-%d %H:%M")}
    ok_r = ok_d = 0
    n = len(SYMBOLS)
    print(f"Cap nhat {n} ma (chi so + co tuc)...\n")
    for i, sym in enumerate(SYMBOLS, 1):
        rec = {}
        r = get_ratios_vnstock(sym)
        if r: rec.update(r); ok_r += 1
        d = get_dividend_vietstock(sym)
        if d: rec.update(d); ok_d += 1
        if rec:
            result[sym] = rec
        tag_r = f"ROE={r.get('roe')}" if r else "chi so X"
        tag_d = "co tuc OK" if d else "co tuc X"
        print(f"  [{i}/{n}] {sym}: {tag_r} | {tag_d}")
        time.sleep(0.4)
    with open("fundamentals.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"\nXONG: {ok_r} ma co chi so, {ok_d} ma co co tuc.")
    print("Da ghi fundamentals.json. Gio day len GitHub (DAY_LEN.bat hoac git push).")


if __name__ == "__main__":
    main()
