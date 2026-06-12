# -*- coding: utf-8 -*-
"""
Đọc CHỈ SỐ TÀI CHÍNH từ file cache `fundamentals.json` (do máy VN tạo & đẩy lên).
Cloud không lấy được chỉ số trực tiếp (finfo chặn server), nên đọc từ file này.

Cấu trúc fundamentals.json:
{
  "_updated": "2026-06-11",
  "FPT": {"roe":22.5,"roa":12.0,"gross_margin":38,"net_margin":16,
          "pe":18.2,"pb":4.1,"de":0.4,"current_ratio":1.5,
          "rev_yoy":20.1,"npat_yoy":19.5,"cfo_latest":1500},
  ...
}
Thiếu file hoặc thiếu mã -> trả {} (app vẫn chạy phần giá/điểm vào bình thường).
"""
import json, os

_CACHE = None
_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fundamentals.json")


def load_all():
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            _CACHE = json.load(f)
    except Exception:
        _CACHE = {}
    return _CACHE


def updated_date():
    return load_all().get("_updated", "chưa có")


def get_metrics(symbol):
    """Trả dict chỉ số cho 1 mã (keys khớp analyzer): roe, roa, gross_margin,
    net_margin, pe, pb, de, current_ratio. Thiếu -> {}."""
    d = load_all().get(symbol.upper())
    return d if isinstance(d, dict) else {}


def get_growth(symbol):
    d = load_all().get(symbol.upper()) or {}
    return {"rev_yoy": d.get("rev_yoy"), "rev_qoq": d.get("rev_qoq"),
            "npat_yoy": d.get("npat_yoy"), "npat_qoq": d.get("npat_qoq")}


def get_cashflow(symbol):
    d = load_all().get(symbol.upper()) or {}
    return {"cfo_latest": d.get("cfo_latest"),
            "cfo_negative_streak": d.get("cfo_negative_streak", 0),
            "fcf_latest": d.get("fcf_latest"), "notes": []}


def has_data():
    c = load_all()
    return len([k for k in c.keys() if not k.startswith("_")]) > 0
