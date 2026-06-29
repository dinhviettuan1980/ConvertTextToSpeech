"""
Text-to-speech ra MP3 bằng gTTS (giọng Google Tiếng Việt — tự nhiên, không robot).
Trả về bytes MP3 để API stream thẳng (không cần lưu file).
"""
from __future__ import annotations

import io


def synthesize(text: str, lang: str = "vi") -> bytes:
    from gtts import gTTS  # import lazy để service không cần gtts nếu chỉ dùng /ocr
    t = (text or "").strip()
    if not t:
        raise ValueError("Thiếu text")
    buf = io.BytesIO()
    gTTS(text=t, lang=lang).write_to_fp(buf)
    return buf.getvalue()
