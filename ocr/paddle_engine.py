"""
Engine OCR dùng PaddleOCR (CPU mode). Implement `BaseOCREngine`.

Thư viện nặng (paddleocr, paddlepaddle, opencv) được import LAZY trong __init__/ocr
để: (a) `import ocr.parser/extractor` chạy được khi chưa cài Paddle (tiện test);
    (b) khởi tạo model 1 lần, tái sử dụng.

Đổi sang Surya/Mistral sau này: viết class mới implement BaseOCREngine rồi khai báo
trong `create_engine()` — KHÔNG đụng parser/extractor/api.
"""
from __future__ import annotations

import os
from typing import List

from .base import BaseOCREngine, OCRResult


def _poly_to_bbox(poly) -> List[int]:
    """4 điểm đa giác -> [x_min, y_min, x_max, y_max] (int)."""
    xs = [float(p[0]) for p in poly]
    ys = [float(p[1]) for p in poly]
    return [int(round(min(xs))), int(round(min(ys))),
            int(round(max(xs))), int(round(max(ys)))]


class PaddleEngine(BaseOCREngine):
    name = "paddle"

    def __init__(self, lang: str = None, use_angle_cls: bool = True):
        # lang 'vi' = tiếng Việt; có thể override bằng ENV OCR_LANG.
        self.lang = lang or os.getenv("OCR_LANG", "vi")
        self.use_angle_cls = use_angle_cls
        self._ocr = None  # lazy

    def _engine(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR  # import nặng, chỉ khi cần
            self._ocr = PaddleOCR(
                use_angle_cls=self.use_angle_cls,
                lang=self.lang,
                use_gpu=False,        # CPU mode theo yêu cầu
                show_log=False,
            )
        return self._ocr

    def ocr(self, image_bytes: bytes) -> List[OCRResult]:
        import numpy as np
        import cv2

        arr = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if arr is None:
            raise ValueError("Không decode được ảnh (định dạng không hợp lệ?)")

        raw = self._engine().ocr(arr, cls=self.use_angle_cls)
        # PaddleOCR 2.x: raw = [ [ [poly, (text, conf)], ... ] ] (list theo từng ảnh)
        if not raw or raw[0] is None:
            return []
        lines = raw[0]

        results: List[OCRResult] = []
        for line in lines:
            try:
                poly, (text, conf) = line[0], line[1]
                results.append(OCRResult(
                    text=str(text),
                    confidence=round(float(conf), 4),
                    bbox=_poly_to_bbox(poly),
                ))
            except Exception:
                # 1 dòng lỗi không được làm hỏng cả ảnh (ưu tiên không bỏ sót phần còn lại)
                continue
        return results


def create_engine(name: str = None) -> BaseOCREngine:
    """Factory chọn engine theo ENV `OCR_ENGINE` (mặc định 'paddle').

    Thêm engine mới (surya/mistral) chỉ cần bổ sung nhánh ở đây.
    """
    name = (name or os.getenv("OCR_ENGINE", "paddle")).lower()
    if name == "paddle":
        return PaddleEngine()
    # if name == "surya":  from .surya_engine import SuryaEngine; return SuryaEngine()
    # if name == "mistral": from .mistral_engine import MistralEngine; return MistralEngine()
    raise ValueError(f"OCR engine chưa hỗ trợ: {name}")
