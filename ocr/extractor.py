"""
Phân loại một chuỗi-có-số thành: number | date | time | address_number | phone | age | unknown.

Nguyên tắc (theo yêu cầu):
  - KHÔNG tự sửa số, KHÔNG suy luận. Chỉ phân loại dựa trên HÌNH DẠNG chuỗi (regex)
    và NGỮ CẢNH (text cùng vùng OCR) một cách thận trọng.
  - Không xác định được -> "unknown" (với số nguyên thuần -> "number").
"""
from __future__ import annotations

import re
import unicodedata

# ----- regex hình dạng (structural) -----
RE_TIME = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?$")            # 06:22, 15:45:30
RE_DATE = re.compile(r"^\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}$")    # 27/06/2026, 27-06-26
RE_PHONE = re.compile(r"^(?:\+?84|0)\d{8,10}$")                 # 0xxxxxxxxx, +84xxxxxxxxx
RE_INT_SHORT = re.compile(r"^\d{1,3}$")                          # 1..999 (ứng viên tuổi/số nhà)
RE_INT = re.compile(r"^\d+$")                                    # số nguyên thuần

# ----- từ khoá ngữ cảnh (đã bỏ dấu, lowercase) -----
AGE_CUES = ("tho", "tuoi")
ADDRESS_CUES = ("sn", "so nha", "so dien", "ngo", "ngach", "duong", "pho",
                "ngo ", "nha so", "to ", "khu ", "p.", "q.")


def _strip_accents(s: str) -> str:
    """Bỏ dấu tiếng Việt + lowercase để so khớp từ khoá ngữ cảnh."""
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "d").lower()


def classify(value: str, context: str = "") -> str:
    """Trả về loại của chuỗi `value`. `context` là text cùng vùng OCR (tuỳ chọn)."""
    v = (value or "").strip()
    if not v:
        return "unknown"

    # 1) Hình dạng rõ ràng — ưu tiên, đáng tin cậy nhất
    if RE_TIME.match(v):
        return "time"
    if RE_DATE.match(v):
        return "date"
    if RE_PHONE.match(v.replace(" ", "")):
        return "phone"

    ctx = _strip_accents(context)

    # 2) Số nguyên ngắn: dựa ngữ cảnh để đoán tuổi / số nhà (thận trọng)
    if RE_INT_SHORT.match(v):
        if any(c in ctx for c in AGE_CUES):
            return "age"
        if any(c in ctx for c in ADDRESS_CUES):
            return "address_number"
        return "number"

    # 3) Số nguyên dài khác
    if RE_INT.match(v):
        return "number"

    # 4) Còn lại: 12A, 193/12, ... -> không chắc chắn
    return "unknown"
