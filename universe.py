# -*- coding: utf-8 -*-
"""
Vũ trụ cổ phiếu để app TỰ QUÉT — người dùng không cần biết trước mã nào.
Cập nhật danh sách theo rổ chỉ số mới nhất khi cần.
"""

# VN30 — nhóm vốn hóa lớn, thanh khoản cao nhất HOSE (tham khảo)
VN30 = ["ACB","BCM","BID","BVH","CTG","FPT","GAS","GVR","HDB","HPG",
        "MBB","MSN","MWG","PLX","POW","SAB","SHB","SSB","SSI","STB",
        "TCB","TPB","VCB","VHM","VIB","VIC","VJC","VNM","VPB","VRE"]

# Bổ sung nhóm midcap thanh khoản tốt -> tạo "VN100 rút gọn"
MIDCAP = ["DGC","DCM","DPM","KDH","NLG","PDR","DXG","KBC","IDC","SZC",
          "VGC","HSG","NKG","PNJ","FRT","DGW","REE","NT2","PC1","GMD",
          "HAH","VSC","PVT","PVS","PVD","BSR","DHG","IMP","VCI","VND",
          "HCM","CTD","HHV","VCG","GEX","DBC","ANV","VHC","FTS","CMG"]

VN100_LITE = VN30 + MIDCAP

UNIVERSES = {
    "VN30 (30 mã lớn nhất)": VN30,
    "VN100 rút gọn (~70 mã)": VN100_LITE,
    "Chỉ Midcap (~40 mã)": MIDCAP,
}
