"""Tạo link Google Maps từ chuỗi địa chỉ."""
from __future__ import annotations

import urllib.parse


def maps_url(address: str) -> str:
    a = (address or "").strip()
    if not a:
        return ""
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(a)
