# -*- coding: utf-8 -*-
"""
Lưu trữ bền cho app: phiên quét gần nhất + sổ mua thử (paper trading).
Lưu ra file JSON trong repo. Trên cloud, file ghi tạm (mất khi rebuild);
để giữ lâu dài, tải file về và push lên GitHub (giống fundamentals.json).
"""
import json, os
from datetime import datetime

SCAN_FILE = "last_scan.json"
PORTFOLIO_FILE = "portfolio.json"


def save_scan(rows, meta=None):
    """Lưu kết quả quét gần nhất + thời điểm."""
    data = {"_saved": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "meta": meta or {}, "rows": rows}
    try:
        with open(SCAN_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        return True
    except Exception:
        return False


def load_scan():
    """Đọc phiên quét đã lưu. Trả dict hoặc None."""
    if not os.path.exists(SCAN_FILE):
        return None
    try:
        with open(SCAN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ---------------- Paper trading ----------------
def load_portfolio():
    """Đọc sổ mua thử. Trả list các vị thế."""
    if not os.path.exists(PORTFOLIO_FILE):
        return []
    try:
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("positions", [])
    except Exception:
        return []


def save_portfolio(positions):
    try:
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump({"_saved": datetime.now().strftime("%Y-%m-%d %H:%M"),
                       "positions": positions}, f, ensure_ascii=False, indent=1)
        return True
    except Exception:
        return False


def add_position(symbol, entry_price, qty=100, note=""):
    """Thêm 1 lệnh mua thử."""
    pos = load_portfolio()
    pos.append({"sym": symbol.upper(), "entry": float(entry_price),
                "qty": int(qty), "date": datetime.now().strftime("%Y-%m-%d"),
                "note": note})
    save_portfolio(pos)
    return pos


def remove_position(index):
    pos = load_portfolio()
    if 0 <= index < len(pos):
        pos.pop(index)
        save_portfolio(pos)
    return pos


def compute_pnl(positions, current_prices):
    """Tính lời/lỗ. current_prices: dict {sym: giá hiện tại}.
    Trả list bổ sung giá hiện tại + % lời lỗ + tổng."""
    out = []
    total_cost = total_value = 0.0
    for p in positions:
        cur = current_prices.get(p["sym"])
        row = dict(p)
        if cur is not None:
            cost = p["entry"] * p["qty"]
            value = cur * p["qty"]
            row["current"] = round(cur, 2)
            row["pnl_pct"] = round((cur - p["entry"]) / p["entry"] * 100, 1)
            row["pnl_value"] = round(value - cost, 1)
            total_cost += cost; total_value += value
        else:
            row["current"] = None; row["pnl_pct"] = None; row["pnl_value"] = None
        out.append(row)
    summary = {"total_cost": round(total_cost, 1),
               "total_value": round(total_value, 1),
               "total_pnl": round(total_value - total_cost, 1),
               "total_pnl_pct": round((total_value - total_cost) / total_cost * 100, 1)
               if total_cost > 0 else 0}
    return out, summary
