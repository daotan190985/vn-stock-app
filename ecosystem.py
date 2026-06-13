# -*- coding: utf-8 -*-
"""
Bảng HỆ SINH THÁI / nhóm doanh nghiệp (TĨNH — người dùng tự bổ sung).
Mục đích: đánh giá "nền tảng vững, hệ sinh thái mạnh" — yếu tố định tính
quan trọng với cổ phiếu mà không API nào cấp.

Cập nhật/bổ sung tự do. Đây là quan điểm tham khảo, KHÔNG phải khuyến nghị.
"""

# mã -> (tên hệ, mô tả độ vững)
ECOSYSTEM = {
    # Hệ Vingroup
    "VIC": ("Vingroup", "Tập đoàn đa ngành lớn nhất VN: BĐS, bán lẻ, công nghiệp (VinFast)."),
    "VHM": ("Vingroup", "BĐS nhà ở lớn nhất, lõi lợi nhuận của hệ Vin."),
    "VRE": ("Vingroup", "Bán lẻ mặt bằng (Vincom Retail), dòng tiền ổn định."),
    # Hệ Masan
    "MSN": ("Masan", "Tiêu dùng - bán lẻ tích hợp (WinCommerce, Masan Consumer)."),
    "MCH": ("Masan", "Masan Consumer - hàng tiêu dùng nhanh, biên lợi nhuận cao."),
    "MML": ("Masan", "Masan MEATLife - chuỗi thịt."),
    # Hệ FPT
    "FPT": ("FPT", "Công nghệ đầu ngành: phần mềm, xuất khẩu CNTT, viễn thông."),
    "FRT": ("FPT", "Bán lẻ (FPT Shop, Long Châu - dược phẩm tăng trưởng mạnh)."),
    "FTS": ("FPT", "Chứng khoán FPTS."),
    # Hệ Gelex
    "GEX": ("Gelex", "Đa ngành: thiết bị điện, hạ tầng, KCN (Viglacera)."),
    "VGC": ("Gelex", "Viglacera - vật liệu xây dựng + KCN."),
    # Hệ Sovico / HDBank
    "HDB": ("Sovico", "Ngân hàng HDBank thuộc hệ Sovico."),
    "VJC": ("Sovico", "Vietjet Air - hàng không giá rẻ."),
    # Hệ Hòa Phát
    "HPG": ("Hòa Phát", "Thép đầu ngành, mở rộng sang BĐS, nông nghiệp."),
    # Hệ Novaland
    "NVL": ("Novaland", "BĐS quy mô lớn, đòn bẩy cao - rủi ro dòng tiền."),
    # Hệ Vietcombank/quốc doanh
    "VCB": ("NHTM quốc doanh", "Ngân hàng quốc doanh chất lượng tài sản tốt nhất."),
    "BID": ("NHTM quốc doanh", "BIDV - quy mô lớn nhất hệ thống."),
    "CTG": ("NHTM quốc doanh", "VietinBank - vốn nhà nước chi phối."),
}


def get_ecosystem(symbol):
    """Trả (tên hệ, mô tả) hoặc (None, None)."""
    v = ECOSYSTEM.get(symbol.upper())
    return v if v else (None, None)
