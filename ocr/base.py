"""
Khai báo INTERFACE & kiểu dữ liệu dùng chung cho toàn module OCR.

Mục đích: business logic (parser, extractor, api) CHỈ phụ thuộc vào interface
`BaseOCREngine` + dataclass `OCRResult` ở đây — KHÔNG phụ thuộc PaddleOCR.
=> Sau này thay PaddleOCR bằng Surya / Mistral OCR chỉ cần viết engine mới
   implement `BaseOCREngine`, không phải sửa parser/extractor/api.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class OCRResult:
    """Một vùng text mà engine OCR đọc được.

    bbox: hình chữ nhật bao (axis-aligned) dạng [x_min, y_min, x_max, y_max]
          theo toạ độ pixel của ảnh gốc.
    """
    text: str
    confidence: float
    bbox: List[int]


@dataclass
class NumberItem:
    """Một chuỗi chứa số được trích ra từ kết quả OCR."""
    value: str            # GIỮ NGUYÊN chuỗi OCR gốc, không tự sửa
    type: str             # number | date | time | address_number | phone | age | unknown
    bbox: List[int]       # bbox của vùng OCR chứa chuỗi này
    confidence: float
    context: str = field(default="")  # text đầy đủ của vùng OCR (giúp debug/phân loại)


class BaseOCREngine(ABC):
    """Hợp đồng cho mọi engine OCR. Đầu vào ảnh (bytes) -> danh sách OCRResult."""

    name: str = "base"

    @abstractmethod
    def ocr(self, image_bytes: bytes) -> List[OCRResult]:  # pragma: no cover - interface
        """Đọc ảnh, trả về list các vùng text kèm confidence + bbox."""
        raise NotImplementedError
