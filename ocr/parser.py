"""
Trích TẤT CẢ chuỗi chứa số từ kết quả OCR — KHÔNG bỏ sót.

Ưu tiên: thà thừa (false positive) còn hơn thiếu. Mỗi chuỗi giữ NGUYÊN văn OCR,
gắn bbox + confidence của vùng OCR chứa nó, rồi nhờ extractor phân loại.
"""
from __future__ import annotations

import re
from typing import List

from .base import OCRResult, NumberItem
from .extractor import classify

# Bắt cụm có ÍT NHẤT 1 chữ số, cho phép phân tách nội bộ (: / . -) và 1 chữ cái đuôi (12A).
# Ví dụ khớp: 1952  06:22  27/06/2026  193/12  12A  (trong "SN.12" -> "12").
NUMBER_CHUNK = re.compile(r"\d+(?:[:/.\-]\d+)*[A-Za-z]?")


def extract_number_chunks(text: str) -> List[str]:
    """Tách mọi cụm chứa số trong 1 đoạn text (giữ nguyên chuỗi gốc)."""
    return NUMBER_CHUNK.findall(text or "")


# Cửa sổ ngữ cảnh LÂN CẬN quanh con số để đoán tuổi/số nhà (tránh gán nhầm cả dòng:
# vd "Thọ 75 tuổi" — chỉ 75 mới là tuổi, không phải 13/05 cùng dòng khác).
_CTX_LEFT = 14
_CTX_RIGHT = 10


_NON_DIGIT = re.compile(r"\D")
_SPLIT = re.compile(r"[:/]")   # ƯU TIÊN tách ':' và '/' (giờ phút, ngày/tháng/năm)


def extract_numbers(ocr_results: List[OCRResult]) -> List[NumberItem]:
    """Từ danh sách vùng OCR -> danh sách NumberItem (theo thứ tự xuất hiện).

    Quy tắc xử lý mỗi cụm số:
      1) TÁCH trên ':' và '/'  ->  '06:22' -> ['06','22'];  '27/06/2026' -> ['27','06','2026'].
         (KHÔNG tách '.' để '19.5.2' do dòng kẻ chấm vẫn gộp về '1952'.)
      2) LỌC: mỗi phần chỉ giữ CHỮ SỐ (bỏ . - chữ cái...).
      3) LOẠI TRÙNG: mỗi giá trị số chỉ xuất hiện 1 lần.
    `type` được phân loại theo phần đã rút gọn + ngữ cảnh lân cận.
    """
    items: List[NumberItem] = []
    seen = set()
    for r in ocr_results:
        text = r.text or ""
        for m in NUMBER_CHUNK.finditer(text):
            chunk = m.group(0)
            window = text[max(0, m.start() - _CTX_LEFT): m.end() + _CTX_RIGHT]
            for part in _SPLIT.split(chunk):        # (1) tách : /
                digits = _NON_DIGIT.sub("", part)   # (2) chỉ giữ chữ số
                if not digits or digits in seen:    # (3) rỗng hoặc trùng -> bỏ
                    continue
                seen.add(digits)
                items.append(NumberItem(
                    value=digits,
                    type=classify(digits, window),
                    bbox=r.bbox,
                    confidence=round(float(r.confidence), 4),
                    context=text,
                ))
    return items
