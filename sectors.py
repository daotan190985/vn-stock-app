# -*- coding: utf-8 -*-
"""
Bảng tra cứu Xu thế Ngành theo giai đoạn kinh tế (TĨNH).
Đây là dữ liệu định tính do người dùng (analyst) tự soạn và cập nhật.
KHÔNG phải dự báo tự động — chỉ là khung tham chiếu sector rotation.

Cập nhật bảng này theo quan điểm của bạn. Mọi nội dung ở đây là
giả định mang tính tham khảo, KHÔNG phải khuyến nghị đầu tư.
"""

# Các giai đoạn kinh tế điển hình và nhóm ngành thường hưởng lợi / bất lợi
ECONOMIC_PHASES = {
    "Suy thoái / Khủng hoảng (vd COVID-19)": {
        "mo_ta": "Cầu suy yếu, bất định cao, dòng tiền tìm đến nhóm phòng thủ và nhóm hưởng lợi trực tiếp từ bối cảnh.",
        "huong_loi": [
            ("Vận tải biển & Logistics", "Đứt gãy chuỗi cung ứng đẩy giá cước lên cao (vd 2020-2021)."),
            ("Dược phẩm & Thiết bị y tế", "Nhu cầu thiết yếu, ít co giãn theo chu kỳ."),
            ("Hàng tiêu dùng thiết yếu", "Thực phẩm, tạp hóa, bán lẻ nhu yếu phẩm duy trì cầu ổn định."),
            ("Tiện ích (Điện, Nước)", "Dòng tiền ổn định, cổ tức cao, tính phòng thủ."),
        ],
        "bat_loi": [
            ("Hàng không & Du lịch", "Cầu sụp đổ khi hạn chế đi lại."),
            ("Bán lẻ không thiết yếu", "Người tiêu dùng cắt giảm chi tiêu xa xỉ."),
            ("Bất động sản nghỉ dưỡng", "Thanh khoản cạn, dòng tiền tắc nghẽn."),
        ],
    },
    "Lạm phát cao / Thắt chặt tiền tệ": {
        "mo_ta": "Lãi suất tăng, chi phí vốn cao, biên lợi nhuận nhóm thâm dụng vốn bị bào mòn.",
        "huong_loi": [
            ("Tài nguyên cơ bản (Dầu khí, Than)", "Giá hàng hóa neo cao theo lạm phát."),
            ("Tiện ích & Điện", "Khả năng chuyển giá, dòng tiền phòng thủ."),
            ("Doanh nghiệp ít nợ, biên gộp cao", "Chịu được chi phí vốn tăng."),
        ],
        "bat_loi": [
            ("Bất động sản", "Phụ thuộc đòn bẩy, lãi vay tăng bào mòn lợi nhuận và cầu."),
            ("Vật liệu xây dựng (Thép, Xi măng)", "Đầu vào tăng, đầu ra yếu khi đầu tư chậm lại."),
            ("Ngân hàng (giai đoạn đầu)", "NIM bị ép, nợ xấu có xu hướng tăng (cần xét case-by-case)."),
            ("Chứng khoán", "Thanh khoản thị trường giảm khi tiền đắt."),
        ],
    },
    "Phục hồi kinh tế / Nới lỏng": {
        "mo_ta": "Lãi suất hạ, cầu phục hồi, dòng tiền quay lại nhóm chu kỳ và tăng trưởng.",
        "huong_loi": [
            ("Bán lẻ & Tiêu dùng", "Sức mua phục hồi, thu nhập cải thiện."),
            ("Du lịch & Hàng không", "Cầu đi lại bật lại sau giai đoạn nén."),
            ("Xây dựng & Đầu tư công", "Giải ngân đầu tư công, dự án hạ tầng khởi động."),
            ("Ngân hàng", "Tín dụng tăng trưởng, NIM cải thiện, nợ xấu hạ nhiệt."),
            ("Chứng khoán", "Thanh khoản và định giá thị trường phục hồi."),
        ],
        "bat_loi": [
            ("Nhóm phòng thủ thuần túy", "Dòng tiền dịch chuyển sang nhóm tăng trưởng/chu kỳ."),
        ],
    },
    "Xu hướng dài hạn (2025–2027)": {
        "mo_ta": "Các chủ đề cấu trúc dài hạn, không phụ thuộc chu kỳ ngắn hạn.",
        "huong_loi": [
            ("Công nghệ & Chuyển đổi số", "Đầu tư CNTT, phần mềm, dịch vụ số tăng trưởng cấu trúc."),
            ("Bán dẫn & AI", "Chuỗi cung ứng bán dẫn, hạ tầng AI, trung tâm dữ liệu."),
            ("Năng lượng tái tạo & Điện", "Chuyển dịch năng lượng, nhu cầu điện tăng."),
            ("Hạ tầng & Đầu tư công", "Giai đoạn đẩy mạnh hạ tầng quốc gia."),
            ("Khu công nghiệp", "Dòng vốn FDI dịch chuyển chuỗi cung ứng."),
        ],
        "bat_loi": [
            ("Ngành công nghệ lạc hậu / thâm dụng lao động giá rẻ", "Áp lực dịch chuyển và tự động hóa."),
        ],
    },
}

# Map nhanh: ngành ICB phổ biến ở VN -> mã cổ phiếu tiêu biểu (tham khảo, KHÔNG phải khuyến nghị)
SECTOR_TICKERS = {
    "Ngân hàng": ["VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "STB", "HDB"],
    "Bất động sản": ["VHM", "VIC", "NVL", "KDH", "DXG", "NLG", "PDR"],
    "Chứng khoán": ["SSI", "VND", "HCM", "VCI", "MBS", "FTS"],
    "Thép & Vật liệu": ["HPG", "HSG", "NKG", "SMC"],
    "Bán lẻ": ["MWG", "PNJ", "FRT", "DGW"],
    "Công nghệ": ["FPT", "CMG", "ELC"],
    "Dầu khí": ["GAS", "PLX", "PVD", "PVS", "BSR"],
    "Điện & Tiện ích": ["POW", "REE", "NT2", "PC1", "GEG"],
    "Hàng không & Du lịch": ["HVN", "VJC", "ACV"],
    "Vận tải biển & Logistics": ["GMD", "HAH", "VSC", "PVT"],
    "Dược phẩm": ["DHG", "IMP", "DBD", "TRA"],
    "Hàng tiêu dùng": ["VNM", "MSN", "SAB", "MCH"],
    "Khu công nghiệp": ["KBC", "BCM", "IDC", "SZC", "VGC"],
    "Xây dựng": ["CTD", "HHV", "VCG", "LCG"],
}
