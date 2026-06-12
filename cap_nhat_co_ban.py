# -*- coding: utf-8 -*-
"""
CẬP NHẬT CHỈ SỐ CƠ BẢN — chạy trên MÁY VN (nhà/công ty), nơi finfo/vnstock chạy được.
Tạo file fundamentals.json để app trên cloud đọc.

CHẠY:
    py -3.12 cap_nhat_co_ban.py
Sau đó đẩy lên GitHub (DAY_LEN.bat hoặc git push) để cloud cập nhật.

Chỉ cần chạy MỖI QUÝ MỘT LẦN (chỉ số tài chính theo quý).
Thử 2 nguồn: VNDirect finfo trước, vnstock sau.
"""
import json, time, sys
from datetime import datetime
import requests

# danh sách mã (đồng bộ với universe.py)
VN30 = ["ACB","BCM","BID","BVH","CTG","FPT","GAS","GVR","HDB","HPG",
        "MBB","MSN","MWG","PLX","POW","SAB","SHB","SSB","SSI","STB",
        "TCB","TPB","VCB","VHM","VIB","VIC","VJC","VNM","VPB","VRE"]
MIDCAP = ["DGC","DCM","DPM","KDH","NLG","PDR","DXG","KBC","IDC","SZC",
          "VGC","HSG","NKG","PNJ","FRT","DGW","REE","NT2","PC1","GMD",
          "HAH","VSC","PVT","PVS","PVD","BSR","DHG","IMP","VCI","VND",
          "HCM","CTD","HHV","VCG","GEX","DBC","ANV","VHC","FTS","CMG"]
SYMBOLS = VN30 + MIDCAP

H = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36",
     "Accept":"application/json, text/plain, */*",
     "Referer":"https://dstock.vndirect.com.vn/"}

RATIO_CODES = {
    "ROE":"roe","ROA":"roa","PRICE_TO_EARNINGS":"pe","PRICE_TO_BOOK":"pb",
    "NET_PROFIT_MARGIN":"net_margin","GROSS_PROFIT_MARGIN":"gross_margin",
    "DEBT_ON_EQUITY":"de","CURRENT_RATIO":"current_ratio",
}

def from_vndirect(sym, tries=4):
    """Lấy chỉ số từ finfo. Trên IP người thật (VN) thường chạy."""
    url=(f"https://finfo-api.vndirect.com.vn/v4/ratios?q=code:{sym}~reportType:QUARTER"
         "&sort=reportDate&size=40")
    for i in range(tries):
        try:
            r=requests.get(url,headers=H,timeout=12)
            if r.status_code==200:
                data=r.json().get("data",[])
                if not data: return None
                out={}
                for it in data:
                    code=it.get("ratioCode"); val=it.get("value")
                    if code in RATIO_CODES and RATIO_CODES[code] not in out and val is not None:
                        key=RATIO_CODES[code]
                        if key in ("roe","roa","net_margin","gross_margin") and abs(val)<5:
                            val=val*100
                        out[key]=round(float(val),2)
                return out or None
            if r.status_code in (429,502,503,504):
                time.sleep(1.5*(i+1)); continue
            return None
        except Exception:
            time.sleep(1.5*(i+1))
    return None

def from_vnstock(sym):
    """Dự phòng: dùng vnstock (nếu đã cài trên máy)."""
    try:
        from vnstock.api.financial import Finance
        f=Finance(source="VCI",symbol=sym,period="quarter")
        df=f.ratio(lang="en",dropna=False)
        if df is None or df.empty: return None
        # đọc cột linh hoạt
        def pick(cands):
            cols={(" ".join(map(str,c)) if isinstance(c,tuple) else str(c)).lower():c for c in df.columns}
            for cand in cands:
                for k,o in cols.items():
                    if cand in k: return o
            return None
        row=df.iloc[-1]
        def g(cands):
            c=pick(cands)
            try: return round(float(row[c]),2) if c is not None else None
            except: return None
        return {"roe":g(["roe"]),"roa":g(["roa"]),"pe":g(["p/e","pe"]),"pb":g(["p/b","pb"]),
                "net_margin":g(["net profit margin","net margin"]),
                "gross_margin":g(["gross profit margin","gross margin"]),
                "de":g(["debt/equity","debt to equity"]),
                "current_ratio":g(["current ratio"])}
    except Exception:
        return None

def main():
    result={"_updated":datetime.now().strftime("%Y-%m-%d %H:%M")}
    ok=0; fail=[]
    print(f"Cap nhat chi so cho {len(SYMBOLS)} ma...\n")
    for i,sym in enumerate(SYMBOLS,1):
        m=from_vndirect(sym) or from_vnstock(sym)
        if m:
            result[sym]=m; ok+=1
            print(f"  [{i}/{len(SYMBOLS)}] {sym}: OK (ROE={m.get('roe')} PE={m.get('pe')})")
        else:
            fail.append(sym)
            print(f"  [{i}/{len(SYMBOLS)}] {sym}: khong lay duoc")
        time.sleep(0.3)
    with open("fundamentals.json","w",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,indent=1)
    print(f"\nXONG: {ok} ma OK, {len(fail)} ma loi.")
    if fail: print("Loi:", ", ".join(fail))
    print("Da ghi fundamentals.json. Gio chay DAY_LEN.bat (hoac git push) de day len cloud.")

if __name__=="__main__":
    main()
