# -*- coding: utf-8 -*-
"""
Engine phân tích cơ bản — RULE-BASED hoàn toàn.

Triết lý: mọi nhận định, cảnh báo, điểm số và khuyến nghị đều suy ra từ
con số thật theo ngưỡng minh bạch. Không có yếu tố "bịa". Mỗi kết luận
đều kèm con số để người dùng tự kiểm chứng.

NGƯỠNG đánh giá là quy ước tham khảo của một analyst thận trọng — bạn có thể
chỉnh trong phần THRESHOLDS bên dưới cho phù hợp khẩu vị / từng ngành.
"""
import pandas as pd
import numpy as np
from data import pick_col, safe_get

# ----------------- NGƯỠNG ĐÁNH GIÁ (chỉnh được) -----------------
THRESHOLDS = {
    "roe_good": 15.0, "roe_weak": 8.0,            # %
    "gross_margin_good": 25.0,                     # %
    "net_margin_good": 10.0, "net_margin_weak": 3.0,
    "de_high": 1.5, "de_safe": 0.7,                # Nợ vay / VCSH (lần)
    "current_ratio_safe": 1.2, "current_ratio_risk": 1.0,
    "pe_cheap": 10.0, "pe_expensive": 25.0,
    "pb_cheap": 1.0, "pb_expensive": 3.0,
    "rev_growth_good": 15.0,                        # % YoY
    "eps_growth_good": 15.0,
}


def _num(x):
    try:
        if x is None or pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def _latest_rows(df, n=8):
    """Trả về n hàng gần nhất, sắp xếp cũ->mới nếu phát hiện cột thời gian."""
    if df is None or df.empty:
        return df
    df = df.copy()
    year_col = pick_col(df, ["yearreport", "year", "năm"], contains=True)
    q_col = pick_col(df, ["lengthreport", "quarter", "quý", "period"], contains=True)
    try:
        if year_col is not None and q_col is not None:
            df = df.sort_values([year_col, q_col])
        elif year_col is not None:
            df = df.sort_values([year_col])
    except Exception:
        pass
    return df.tail(n)


# ----------------- TRÍCH XUẤT CHỈ SỐ -----------------

def extract_metrics(ratio_df):
    """Lấy bộ chỉ số kỳ gần nhất + kỳ liền trước từ bảng ratio của vnstock."""
    if ratio_df is None or ratio_df.empty:
        return {}, {}
    df = _latest_rows(ratio_df, n=12)
    if df.empty:
        return {}, {}

    # bản đồ tên cột khả dĩ (vnstock VCI tiếng Anh)
    M = {
        "roe":   ["roe", "roe (%)", "return on equity"],
        "roa":   ["roa", "roa (%)", "return on assets"],
        "gross_margin": ["gross profit margin", "gross margin", "biên lợi nhuận gộp"],
        "net_margin":   ["net profit margin", "post-tax profit margin", "net margin", "biên lợi nhuận ròng"],
        "pe":    ["p/e", "pe", "price to earning"],
        "pb":    ["p/b", "pb", "price to book"],
        "ev_ebitda": ["ev/ebitda", "ev per ebitda"],
        "de":    ["debt/equity", "debt to equity", "(st+lt borrowings)/equity", "liabilities/equity"],
        "current_ratio": ["current ratio", "tỷ số thanh toán hiện hành"],
        "quick_ratio":   ["quick ratio"],
        "eps":   ["eps", "eps (vnd)"],
        "bvps":  ["bvps", "book value per share"],
    }

    def col_for(key):
        return pick_col(df, M[key], contains=True)

    rows = df.reset_index(drop=True)
    last = rows.iloc[-1]
    prev = rows.iloc[-2] if len(rows) >= 2 else None

    def grab(row, key):
        return _num(safe_get(row, col_for(key)))

    cur = {k: grab(last, k) for k in M}
    pre = {k: (grab(prev, k) if prev is not None else None) for k in M}
    return cur, pre


def compute_growth(income_df):
    """Tăng trưởng doanh thu & LNST: QoQ và YoY (gần đúng từ income statement)."""
    out = {"rev_yoy": None, "rev_qoq": None, "npat_yoy": None, "npat_qoq": None}
    if income_df is None or income_df.empty:
        return out
    df = _latest_rows(income_df, n=8).reset_index(drop=True)
    rev_col = pick_col(df, ["revenue", "net revenue", "sales", "doanh thu thuần", "total operating revenue"], contains=True)
    npat_col = pick_col(df, ["attribute to parent", "net profit", "profit after tax",
                             "profit for the year", "lợi nhuận sau thuế", "net income"], contains=True)

    def series(col):
        if col is None:
            return None
        return pd.to_numeric(df[col], errors="coerce")

    rev, npat = series(rev_col), series(npat_col)

    def pct(s, lag):
        if s is None or len(s) <= lag:
            return None
        a, b = s.iloc[-1], s.iloc[-1 - lag]
        if b is None or pd.isna(b) or b == 0:
            return None
        return round((a - b) / abs(b) * 100, 1)

    out["rev_qoq"] = pct(rev, 1)
    out["rev_yoy"] = pct(rev, 4)
    out["npat_qoq"] = pct(npat, 1)
    out["npat_yoy"] = pct(npat, 4)
    return out


def analyze_cashflow(cf_df):
    """Đánh giá dòng tiền HĐKD và FCF (gần đúng)."""
    out = {"cfo_latest": None, "cfo_negative_streak": 0, "fcf_latest": None, "notes": []}
    if cf_df is None or cf_df.empty:
        return out
    df = _latest_rows(cf_df, n=8).reset_index(drop=True)
    cfo_col = pick_col(df, ["net cash flow from operating", "operating activities",
                            "cash flow from operating", "lưu chuyển tiền thuần từ hoạt động kinh doanh"], contains=True)
    capex_col = pick_col(df, ["purchase of fixed", "capex", "investment in fixed assets",
                              "mua sắm tài sản cố định"], contains=True)
    if cfo_col is not None:
        cfo = pd.to_numeric(df[cfo_col], errors="coerce")
        out["cfo_latest"] = _num(cfo.iloc[-1])
        streak = 0
        for v in reversed(list(cfo)):
            if pd.notna(v) and v < 0:
                streak += 1
            else:
                break
        out["cfo_negative_streak"] = streak
        if capex_col is not None:
            capex = pd.to_numeric(df[capex_col], errors="coerce")
            try:
                out["fcf_latest"] = _num(cfo.iloc[-1] + capex.iloc[-1])  # capex thường âm
            except Exception:
                pass
    return out


# ----------------- SCORING & KHUYẾN NGHỊ -----------------

def score_stock(cur, growth, cf):
    """Tính điểm 0-100 trên 4 trụ: Sinh lời, Sức khỏe TC, Tăng trưởng, Định giá.
    Trả về dict điểm + chi tiết lý do (truy ngược được)."""
    T = THRESHOLDS
    pillars = {}
    reasons = {"profitability": [], "health": [], "growth": [], "valuation": []}

    # --- Trụ 1: Khả năng sinh lời (0-25) ---
    p = 0
    roe = cur.get("roe")
    if roe is not None:
        if roe >= T["roe_good"]:
            p += 12; reasons["profitability"].append(f"ROE {roe:.1f}% — cao (≥{T['roe_good']}%)")
        elif roe >= T["roe_weak"]:
            p += 7;  reasons["profitability"].append(f"ROE {roe:.1f}% — trung bình")
        else:
            p += 2;  reasons["profitability"].append(f"ROE {roe:.1f}% — thấp (<{T['roe_weak']}%)")
    nm = cur.get("net_margin")
    if nm is not None:
        if nm >= T["net_margin_good"]:
            p += 8; reasons["profitability"].append(f"Biên LN ròng {nm:.1f}% — tốt")
        elif nm >= T["net_margin_weak"]:
            p += 4; reasons["profitability"].append(f"Biên LN ròng {nm:.1f}% — mỏng")
        else:
            p += 1; reasons["profitability"].append(f"Biên LN ròng {nm:.1f}% — rất mỏng")
    gm = cur.get("gross_margin")
    if gm is not None and gm >= T["gross_margin_good"]:
        p += 5; reasons["profitability"].append(f"Biên gộp {gm:.1f}% — khỏe")
    pillars["profitability"] = min(p, 25)

    # --- Trụ 2: Sức khỏe tài chính (0-25) ---
    p = 0
    de = cur.get("de")
    if de is not None:
        if de <= T["de_safe"]:
            p += 12; reasons["health"].append(f"Nợ/VCSH {de:.2f} — an toàn")
        elif de <= T["de_high"]:
            p += 7;  reasons["health"].append(f"Nợ/VCSH {de:.2f} — chấp nhận được")
        else:
            p += 2;  reasons["health"].append(f"Nợ/VCSH {de:.2f} — đòn bẩy cao (>{T['de_high']})")
    cr = cur.get("current_ratio")
    if cr is not None:
        if cr >= T["current_ratio_safe"]:
            p += 7; reasons["health"].append(f"Thanh toán hiện hành {cr:.2f} — tốt")
        elif cr >= T["current_ratio_risk"]:
            p += 4; reasons["health"].append(f"Thanh toán hiện hành {cr:.2f} — tạm ổn")
        else:
            p += 1; reasons["health"].append(f"Thanh toán hiện hành {cr:.2f} — rủi ro (<1)")
    if cf.get("cfo_latest") is not None:
        if cf["cfo_latest"] > 0 and cf.get("cfo_negative_streak", 0) == 0:
            p += 6; reasons["health"].append("Dòng tiền HĐKD dương")
        elif cf.get("cfo_negative_streak", 0) >= 2:
            reasons["health"].append(f"⚠ CFO âm {cf['cfo_negative_streak']} kỳ liên tiếp")
    pillars["health"] = min(p, 25)

    # --- Trụ 3: Tăng trưởng (0-25) ---
    p = 0
    ry = growth.get("rev_yoy")
    if ry is not None:
        if ry >= T["rev_growth_good"]:
            p += 12; reasons["growth"].append(f"Doanh thu +{ry:.1f}% YoY — tăng tốt")
        elif ry >= 0:
            p += 6;  reasons["growth"].append(f"Doanh thu +{ry:.1f}% YoY — đi ngang/nhẹ")
        else:
            p += 1;  reasons["growth"].append(f"Doanh thu {ry:.1f}% YoY — suy giảm")
    ny = growth.get("npat_yoy")
    if ny is not None:
        if ny >= T["eps_growth_good"]:
            p += 13; reasons["growth"].append(f"LNST +{ny:.1f}% YoY — tăng mạnh")
        elif ny >= 0:
            p += 6;  reasons["growth"].append(f"LNST +{ny:.1f}% YoY")
        else:
            p += 1;  reasons["growth"].append(f"LNST {ny:.1f}% YoY — giảm")
    pillars["growth"] = min(p, 25)

    # --- Trụ 4: Định giá (0-25) ---
    p = 0
    pe = cur.get("pe")
    if pe is not None and pe > 0:
        if pe <= T["pe_cheap"]:
            p += 13; reasons["valuation"].append(f"P/E {pe:.1f} — rẻ")
        elif pe <= T["pe_expensive"]:
            p += 7;  reasons["valuation"].append(f"P/E {pe:.1f} — hợp lý")
        else:
            p += 2;  reasons["valuation"].append(f"P/E {pe:.1f} — đắt (>{T['pe_expensive']})")
    elif pe is not None and pe <= 0:
        reasons["valuation"].append("P/E âm — DN đang lỗ")
    pb = cur.get("pb")
    if pb is not None and pb > 0:
        if pb <= T["pb_cheap"]:
            p += 12; reasons["valuation"].append(f"P/B {pb:.2f} — dưới giá trị sổ sách")
        elif pb <= T["pb_expensive"]:
            p += 7;  reasons["valuation"].append(f"P/B {pb:.2f} — hợp lý")
        else:
            p += 2;  reasons["valuation"].append(f"P/B {pb:.2f} — cao")
    pillars["valuation"] = min(p, 25)

    total = sum(pillars.values())
    return {"total": total, "pillars": pillars, "reasons": reasons}


def recommendation(total_score, warnings_list):
    """Khuyến nghị rule-based. Cảnh báo nghiêm trọng kéo tụt khuyến nghị."""
    severe = sum(1 for w in warnings_list if w.get("level") == "high")
    label, conf = "GIỮ", "Trung bình"
    if total_score >= 70:
        label, conf = "MUA", "Cao"
    elif total_score >= 55:
        label, conf = "MUA / TÍCH LŨY", "Trung bình"
    elif total_score >= 40:
        label, conf = "GIỮ", "Trung bình"
    elif total_score >= 25:
        label, conf = "BÁN / GIẢM TỶ TRỌNG", "Trung bình"
    else:
        label, conf = "TRÁNH", "Cao"

    # cảnh báo nghiêm trọng hạ bậc
    if severe >= 2 and label in ("MUA", "MUA / TÍCH LŨY"):
        label, conf = "GIỮ (thận trọng do cảnh báo)", "Thấp"
    elif severe >= 2 and label == "GIỮ":
        label, conf = "BÁN / GIẢM TỶ TRỌNG", "Trung bình"
    return label, conf


def detect_warnings(cur, growth, cf):
    """Cảnh báo sớm rule-based. Mỗi cảnh báo có level: high/medium/low."""
    w = []
    if cf.get("cfo_negative_streak", 0) >= 2:
        w.append({"level": "high", "msg": f"Dòng tiền HĐKD âm {cf['cfo_negative_streak']} kỳ liên tiếp — chất lượng lợi nhuận đáng ngờ."})
    if growth.get("npat_yoy") is not None and growth["npat_yoy"] > 30 and (cf.get("cfo_latest") is not None and cf["cfo_latest"] < 0):
        w.append({"level": "high", "msg": "LNST tăng mạnh nhưng dòng tiền kinh doanh âm — nghi lợi nhuận ảo (ghi nhận trên giấy)."})
    de = cur.get("de")
    if de is not None and de > THRESHOLDS["de_high"]:
        w.append({"level": "medium", "msg": f"Đòn bẩy cao (Nợ/VCSH={de:.2f}) — nhạy cảm với lãi suất."})
    cr = cur.get("current_ratio")
    if cr is not None and cr < THRESHOLDS["current_ratio_risk"]:
        w.append({"level": "medium", "msg": f"Thanh toán hiện hành <1 ({cr:.2f}) — áp lực thanh khoản ngắn hạn."})
    if cur.get("pe") is not None and cur["pe"] is not None and cur["pe"] < 0:
        w.append({"level": "high", "msg": "P/E âm — doanh nghiệp đang thua lỗ."})
    if growth.get("rev_yoy") is not None and growth["rev_yoy"] < -15:
        w.append({"level": "medium", "msg": f"Doanh thu giảm mạnh {growth['rev_yoy']:.1f}% YoY."})
    pe = cur.get("pe"); pb = cur.get("pb")
    if pe is not None and pe > THRESHOLDS["pe_expensive"] and pb is not None and pb > THRESHOLDS["pb_expensive"]:
        w.append({"level": "low", "msg": "Định giá cao trên cả P/E lẫn P/B — rủi ro điều chỉnh nếu kỳ vọng hụt."})
    return w
