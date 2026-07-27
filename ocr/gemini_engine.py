"""
Engine OCR dùng Gemini Vision (free tier) — đọc tốt chữ VIẾT TAY tiếng Việt.

Thay cho groq_engine.py: Groq đã ngừng phục vụ MỌI model vision (kể cả
meta-llama/llama-4-scout-17b-16e-instruct, model vision cuối cùng còn lại — đã tự kiểm tra
GET https://api.groq.com/openai/v1/models, không còn model nào có khả năng nhận ảnh).

Lưu ý khi lấy GEMINI_API_KEY (aistudio.google.com/apikey):
  - Key tạo trong project ĐÃ gắn billing (dù hết tiền) sẽ bị chặn ngay cả free tier
    (lỗi "prepayment credits are depleted") -> phải "Create API key in new project"
    (project mới, KHÔNG gắn billing) mới dùng được free tier.
  - Model `gemini-2.0-flash`/`gemini-2.5-flash` bị chặn free tier với project mới tạo
    ("no longer available to new users" / quota free tier = 0) -> dùng alias
    `gemini-flash-latest` (đã tự test hoạt động, hiện trỏ tới gemini-3.6-flash).

Implement `BaseOCREngine`. Chỉ dùng thư viện chuẩn (urllib) — KHÔNG cần SDK google-genai.

ENV:
  GEMINI_API_KEY        (bắt buộc)
  GEMINI_VISION_MODEL   (mặc định gemini-flash-latest)
  GEMINI_OCR_CONFIDENCE (mặc định 0.9)
"""
from __future__ import annotations

import os
import json
import base64
import urllib.request
import urllib.error
from typing import List

from .base import BaseOCREngine, OCRResult

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_PROMPT = (
    "Bạn là công cụ OCR. Hãy CHÉP LẠI CHÍNH XÁC toàn bộ chữ và SỐ xuất hiện trong ảnh "
    "(kể cả chữ viết tay), giữ nguyên từng chữ số. TUYỆT ĐỐI không đoán, không thêm bớt, "
    "không suy luận. Mỗi dòng văn bản trong ảnh xuất ra một dòng riêng. "
    "Chỉ trả về văn bản thuần, không giải thích, không markdown."
)


def _gemini_model():
    return os.getenv("GEMINI_VISION_MODEL", "gemini-flash-latest")


def vision_complete(image_bytes: bytes, prompt: str, max_tokens: int = 2048,
                    temperature: float = 0, model: str = None) -> str:
    """Gọi Gemini vision với 1 ảnh + prompt, trả về nội dung text. Dùng chung cho OCR và
    trích cáo phó/đơn thuốc/xét nghiệm/scan."""
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("Thiếu GEMINI_API_KEY")
    mime = "image/png" if image_bytes[:8].startswith(b"\x89PNG") else "image/jpeg"
    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"inlineData": {"mimeType": mime, "data": base64.b64encode(image_bytes).decode()}},
                {"text": prompt},
            ],
        }],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    url = GEMINI_URL.format(model=model or _gemini_model()) + f"?key={key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini lỗi {e.code}: {detail}") from e
    candidates = body.get("candidates") or [{}]
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def ocr_full_text(image_bytes: bytes, max_tokens: int = 4096) -> str:
    """Trả nguyên văn bản đọc được từ ảnh (không tách OCRResult) — dùng cho nơi cần đọc to
    toàn bộ nội dung (vd convert_to_mp3.py), khác GeminiEngine.ocr() vốn tách theo dòng."""
    return vision_complete(image_bytes, _PROMPT, max_tokens=max_tokens).strip()


class GeminiEngine(BaseOCREngine):
    name = "gemini"

    def __init__(self):
        self.confidence = float(os.getenv("GEMINI_OCR_CONFIDENCE", "0.9"))

    def ocr(self, image_bytes: bytes) -> List[OCRResult]:
        text = vision_complete(image_bytes, _PROMPT, max_tokens=2048)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return [OCRResult(text=ln, confidence=self.confidence, bbox=[]) for ln in lines]
