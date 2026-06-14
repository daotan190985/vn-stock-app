# -*- coding: utf-8 -*-
"""
TỔNG HỢP & KẾT LUẬN — app tự nhận định, không bắt người dùng tự soi.
1) market_conclusion(): đọc toàn bộ % của danh sách -> độ lan tỏa (breadth),
   pha thị trường, khuyến nghị hành động.
2) seasonality(): mùa vụ theo tháng/quý từ lịch sử nhiều năm (VN-Index hoặc mã).
   LƯU Ý: mùa vụ là thống kê QUÁ KHỨ, không đảm bảo lặp lại.
"""
import pandas as pd
import numpy as np
import vndirect as VND

VN_MONTHS = ["", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
             "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"]


def market_conclusion(rows, liquidity_value=None, threshold=15000, current_month=None):
    """Tổng hợp từ kết quả quét -> dict {verdict, action, breadth, lines[]}."""
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    n = len(df)
    out = {"lines": []}

    def breadth(col):
        if col not in df.columns:
            return None
        v = pd.to_numeric(df[col], errors="coerce").dropna()
        if v.empty:
            return None
        return {"up": int((v > 0).sum()), "down": int((v < 0).sum()),
                "up_pct": round((v > 0).mean() * 100), "median": round(v.median(), 1),
                "total": len(v)}

    b1 = breadth("%1M"); b3 = breadth("%3M")
    n_vao = int((df["status"] == "VAO").sum()) if "status" in df else 0
    n_cho = int((df["status"] == "CHO").sum()) if "status" in df else 0
    n_tranh = int((df["status"] == "TRANH").sum()) if "status" in df else 0

    # độ lan tỏa
    if b1:
        out["lines"].append(
            f"Trong 1 tháng: {b1['up']}/{b1['total']} mã tăng ({b1['up_pct']}%), "
            f"trung vị {b1['median']:+.1f}%.")
    if b3:
        out["lines"].append(
            f"Trong 3 tháng: {b3['up']}/{b3['total']} mã tăng ({b3['up_pct']}%), "
            f"trung vị {b3['median']:+.1f}%.")

    # xác định pha + khuyến nghị
    up_pct_3m = b3["up_pct"] if b3 else 50
    med_3m = b3["median"] if b3 else 0
    rsi_series = pd.to_numeric(df.get("RSI", pd.Series(dtype=float)), errors="coerce").dropna()
    avg_rsi = rsi_series.mean() if not rsi_series.empty else 50

    if up_pct_3m >= 70 and avg_rsi >= 62:
        verdict = "Thị trường TĂNG NÓNG diện rộng"
        action = ("⚠️ Phần lớn mã đã tăng mạnh và RSI cao — RỦI RO đu đỉnh. "
                  "Ưu tiên CHỜ pullback, không mua đuổi. Chỉ vào mã vừa chỉnh về vùng hỗ trợ.")
    elif up_pct_3m <= 30 and med_3m < -5:
        verdict = "Thị trường GIẢM diện rộng"
        action = ("Phần lớn mã đang giảm. Đây có thể là vùng chiết khấu — NHƯNG chưa vội bắt đáy. "
                  "Chờ tín hiệu tạo đáy (RSI hồi từ vùng thấp, MACD cắt lên) rồi mới canh nhóm khỏe nhất.")
    elif 40 <= up_pct_3m <= 60:
        verdict = "Thị trường PHÂN HÓA"
        action = ("Dòng tiền chọn lọc, không đồng đều. Tập trung mã RIÊNG có nền tảng tốt + vừa về "
                  "vùng chờ, bỏ qua tín hiệu cả thị trường.")
    elif up_pct_3m > 60:
        verdict = "Thị trường ĐANG HỒI PHỤC / tăng"
        action = ("Đa số mã hồi phục. Canh mua mã thuận xu hướng vừa pullback, "
                  "tránh mã đã chạy quá xa.")
    else:
        verdict = "Thị trường YẾU / dò đáy"
        action = ("Số mã giảm nhỉnh hơn. Thận trọng, ưu tiên quan sát, "
                  "chỉ vào mã thật khỏe có dòng tiền xác nhận.")

    # ghép thanh khoản
    if liquidity_value is not None:
        if liquidity_value < threshold:
            action += (f" Thanh khoản (~{liquidity_value:,.0f} tỷ) DƯỚI ngưỡng {threshold:,.0f} — "
                       "thị trường yếu lực, càng nên chờ.")
        else:
            action += f" Thanh khoản (~{liquidity_value:,.0f} tỷ) đủ tốt."

    out["verdict"] = verdict
    out["action"] = action
    out["breadth_1m"] = b1; out["breadth_3m"] = b3
    out["counts"] = {"vao": n_vao, "cho": n_cho, "tranh": n_tranh}
    return out


def seasonality(symbol="VNINDEX", years=8):
    """Mùa vụ: lợi suất TB từng tháng & quý qua nhiều năm.
    Trả dict {monthly:{1..12:{avg,win_rate,n}}, quarterly, best, worst, note} hoặc None."""
    from datetime import datetime, timedelta
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=365 * years + 30)).strftime("%Y-%m-%d")
        df = VND.vnd_history(symbol, start, end)
        if df is None or df.empty:
            return None
        d = df.copy()
        tcol = "time" if "time" in d.columns else d.columns[0]
        d[tcol] = pd.to_datetime(d[tcol], errors="coerce")
        d = d.dropna(subset=[tcol]).set_index(tcol).sort_index()
        close = pd.to_numeric(d["close"], errors="coerce").dropna()
        # close cuối mỗi tháng -> lợi suất tháng
        m = close.resample("M").last()
        ret = m.pct_change().dropna() * 100
        if ret.empty:
            return None
        by_month = {}
        for mo in range(1, 13):
            vals = ret[ret.index.month == mo]
            if len(vals):
                by_month[mo] = {"avg": round(float(vals.mean()), 2),
                                "win_rate": round(float((vals > 0).mean() * 100)),
                                "n": int(len(vals))}
        # theo quý
        q = close.resample("Q").last().pct_change().dropna() * 100
        by_q = {}
        for qq in range(1, 5):
            vals = q[q.index.quarter == qq]
            if len(vals):
                by_q[qq] = {"avg": round(float(vals.mean()), 2),
                            "win_rate": round(float((vals > 0).mean() * 100)),
                            "n": int(len(vals))}
        # tháng tốt/xấu nhất
        if by_month:
            best = max(by_month.items(), key=lambda x: x[1]["avg"])
            worst = min(by_month.items(), key=lambda x: x[1]["avg"])
        else:
            best = worst = None
        return {"monthly": by_month, "quarterly": by_q,
                "best": best, "worst": worst,
                "years": years, "symbol": symbol,
                "note": "Thống kê quá khứ — KHÔNG đảm bảo lặp lại, chỉ tham khảo thời điểm."}
    except Exception:
        return None


def seasonality_text(seas, current_month=None):
    """Tạo câu nhận định mùa vụ cho tháng hiện tại."""
    if not seas or not seas.get("monthly"):
        return ""
    from datetime import datetime
    mo = current_month or datetime.now().month
    mm = seas["monthly"].get(mo)
    lines = []
    if mm:
        tag = "thường TĂNG" if mm["avg"] > 0 else "thường GIẢM"
        lines.append(f"{VN_MONTHS[mo]}: lịch sử {seas['years']} năm {tag} "
                     f"(TB {mm['avg']:+.1f}%, tỷ lệ tăng {mm['win_rate']}%).")
    if seas.get("best") and seas.get("worst"):
        bm, bv = seas["best"]; wm, wv = seas["worst"]
        lines.append(f"Tháng mạnh nhất: {VN_MONTHS[bm]} ({bv['avg']:+.1f}%); "
                     f"yếu nhất: {VN_MONTHS[wm]} ({wv['avg']:+.1f}%).")
    return " ".join(lines)
