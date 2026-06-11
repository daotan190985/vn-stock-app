# VN Stock Fundamental Analyzer

Phân tích cơ bản chuyên sâu cổ phiếu Việt Nam — rule-based, minh bạch.

## Cài đặt
```
pip install -r requirements.txt
streamlit run app.py
```

## Tính năng
- **Đa nhiệm**: nhập nhiều mã (vd `FPT, HPG, VCB`) phân tích cùng lúc
- **Trần / Sàn / Tham chiếu** theo biên độ sàn (HOSE ±7%, HNX ±10%, UPCoM ±15%)
- **Trạng thái mã theo nến**: xu hướng (MA20/MA50), vị trí trong biên độ, breakout/breakdown đỉnh-đáy 20 phiên, khối lượng đột biến, áp sát trần/sàn
- **Biểu đồ nến TradingView** nhúng (Daily)
- **Phân tích BCTC**: ROE/ROA, biên gộp/ròng, P/E, P/B, Nợ/VCSH, thanh khoản, tăng trưởng YoY/QoQ, dòng tiền HĐKD & FCF
- **Scoring 4 trụ** (Sinh lời / Sức khỏe TC / Tăng trưởng / Định giá), mỗi điểm truy ngược được về số liệu
- **Cảnh báo sớm**: nghi lợi nhuận ảo (LNST tăng nhưng CFO âm), đòn bẩy cao, P/E âm, thanh khoản <1...
- **Khuyến nghị** MUA / GIỮ / BÁN / TRÁNH + độ tin cậy
- **Xu thế ngành**: bảng tra cứu tĩnh theo giai đoạn kinh tế (sửa trong `sectors.py`)

## Cấu trúc
- `app.py` — giao diện chính
- `data.py` — lấy dữ liệu (vnstock VCI/KBS), có cache
- `analyzer.py` — engine phân tích rule-based, ngưỡng chỉnh trong `THRESHOLDS`
- `market.py` — trần/sàn/tham chiếu + trạng thái nến
- `sectors.py` — bảng xu thế ngành (tĩnh, tự cập nhật)

## Lưu ý
- vnstock dùng nguồn VCI/KBS (TCBS đã ngừng hỗ trợ từ 08/2025)
- Tên cột BCTC có thể đổi giữa các version — code đã dò cột linh hoạt, nếu thiếu chỉ số nào sẽ hiện "—"
- Nội dung tham khảo, KHÔNG phải khuyến nghị đầu tư

## CẬP NHẬT: Bàn làm việc Analyst (screener-first)
- Mở app → **Bảng theo dõi & Điểm vào**: tự quét VN30/VN100, không cần gõ mã trước
- Mỗi mã có trạng thái: 🟢 ĐIỂM VÀO / 🟡 CHỜ / 🔵 THEO DÕI / 🔴 TRÁNH
- Logic điểm vào kiểu app vàng: thuận xu hướng, pullback về MA, test hỗ trợ, breakout có volume; chặn đu đỉnh & RSI quá mua
- Panel **vĩ mô**: VN-Index trend (live) + chọn giai đoạn → tô đậm ngành hưởng lợi (gió ngành) vào xếp hạng
- Tab **Phân tích chi tiết**: nhập 1 mã ở sidebar để xem báo cáo đầy đủ + TradingView + trần/sàn
