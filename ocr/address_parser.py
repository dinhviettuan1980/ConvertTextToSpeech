"""
Ghép/chuẩn hoá địa chỉ tổ chức tang lễ.

AI (Gemini) đã tìm và ghép địa chỉ trong ảnh (trường `address`). Module này:
  - clean(): chuẩn hoá khoảng trắng/dấu phẩy của chuỗi địa chỉ.
  - compose(): ghép từ các phần rời (nếu sau này AI trả parts) — chỉ nối phần CÓ,
    KHÔNG suy diễn phần thiếu.
"""
from __future__ import annotations

import re

# Thứ tự ghép từ nhỏ -> lớn.
_ORDER = ["so_nha", "ngach", "ngo", "duong", "to", "thon", "phuong", "xa", "quan", "huyen", "thanh_pho", "tinh"]
_LABEL = {
    "so_nha": "Số nhà", "ngach": "Ngách", "ngo": "Ngõ", "duong": "Đường", "to": "Tổ",
    "thon": "Thôn", "phuong": "Phường", "xa": "Xã", "quan": "Quận", "huyen": "Huyện",
    "thanh_pho": "", "tinh": "",
}


def clean(address: str) -> str:
    a = (address or "").strip()
    a = re.sub(r"\s+", " ", a)
    a = re.sub(r"\s*,\s*", ", ", a)
    a = re.sub(r"(,\s*)+", ", ", a).strip(" ,")
    return a


def compose(parts: dict) -> str:
    """parts: dict { so_nha, ngach, ngo, duong, phuong, quan, thanh_pho, ... } -> chuỗi."""
    if not parts:
        return ""
    segs = []
    for k in _ORDER:
        v = (parts.get(k) or "").strip()
        if not v:
            continue
        lbl = _LABEL.get(k, "")
        segs.append(f"{lbl} {v}".strip())
    return clean(", ".join(segs))
