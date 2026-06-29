"""
Engine OCR dùng Groq Vision (MIỄN PHÍ) — đọc tốt chữ VIẾT TAY tiếng Việt,
nơi PaddleOCR (model chữ in) thất bại.

Implement `BaseOCREngine`. Chỉ dùng thư viện chuẩn (urllib) — KHÔNG cần paddle/opencv.

Lưu ý:
  - Vision LLM trả về VĂN BẢN, không có bbox pixel -> bbox để trống []. Mục tiêu chính
    "lấy tất cả con số" vẫn đạt; bbox là phụ.
  - confidence không phải độ tin OCR thật (LLM không cung cấp) -> đặt hằng số (mặc định 0.9).
  - Prompt yêu cầu CHÉP ĐÚNG, KHÔNG đoán — hạn chế bịa số.

ENV:
  GROQ_API_KEY        (bắt buộc)
  GROQ_VISION_MODEL   (mặc định meta-llama/llama-4-maverick-17b-128e-instruct)
  GROQ_OCR_CONFIDENCE (mặc định 0.9)
"""
from __future__ import annotations

import os
import json
import base64
import urllib.request
from typing import List

from .base import BaseOCREngine, OCRResult

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_PROMPT = (
    "Bạn là công cụ OCR. Hãy CHÉP LẠI CHÍNH XÁC toàn bộ chữ và SỐ xuất hiện trong ảnh "
    "(kể cả chữ viết tay), giữ nguyên từng chữ số. TUYỆT ĐỐI không đoán, không thêm bớt, "
    "không suy luận. Mỗi dòng văn bản trong ảnh xuất ra một dòng riêng. "
    "Chỉ trả về văn bản thuần, không giải thích, không markdown."
)


class GroqEngine(BaseOCREngine):
    name = "groq"

    def __init__(self):
        self.key = os.getenv("GROQ_API_KEY", "")
        self.model = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
        self.confidence = float(os.getenv("GROQ_OCR_CONFIDENCE", "0.9"))

    def ocr(self, image_bytes: bytes) -> List[OCRResult]:
        if not self.key:
            raise RuntimeError("Thiếu GROQ_API_KEY")

        mime = "image/png" if image_bytes[:8].startswith(b"\x89PNG") else "image/jpeg"
        data_uri = f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"

        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 2048,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }],
        }
        # QUAN TRỌNG: Groq đứng sau Cloudflare, chặn User-Agent mặc định của urllib
        # ("Python-urllib/x.y") -> trả "error code: 1010" (HTTP 403). Đặt UA giống curl để qua.
        ua = os.getenv("OCR_HTTP_UA", "curl/8.5.0")
        req = urllib.request.Request(
            GROQ_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "User-Agent": ua,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        text = (body.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return [OCRResult(text=ln, confidence=self.confidence, bbox=[]) for ln in lines]
