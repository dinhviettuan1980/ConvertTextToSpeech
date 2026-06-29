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


def extract_numbers(ocr_results: List[OCRResult]) -> List[NumberItem]:
    """Từ danh sách vùng OCR -> danh sách NumberItem đã phân loại, theo thứ tự xuất hiện."""
    items: List[NumberItem] = []
    for r in ocr_results:
        text = r.text or ""
        for m in NUMBER_CHUNK.finditer(text):
            chunk = m.group(0)
            window = text[max(0, m.start() - _CTX_LEFT): m.end() + _CTX_RIGHT]
            items.append(NumberItem(
                value=chunk,
                type=classify(chunk, window),   # phân loại theo lân cận
                bbox=r.bbox,
                confidence=round(float(r.confidence), 4),
                context=text,                   # vẫn trả full dòng để debug
            ))
    return items
