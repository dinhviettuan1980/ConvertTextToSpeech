"""
Trích thông tin CÁO PHÓ từ ảnh bằng Groq vision -> JSON chuẩn (spec).

1 lần gọi Groq trả về các trường + full_text + speech_text. Sau đó:
  - address  -> map_service.maps_url
  - full_text -> parser.extract_numbers  -> lottery_numbers (giữ logic số hiện tại)
  - speech_text rỗng -> speech_generator (fallback)

KHÔNG bịa: trường thiếu để chuỗi rỗng.
"""
from __future__ import annotations

import re
import json
from dataclasses import asdict

from .groq_engine import vision_complete
from .base import OCRResult
from .parser import extract_numbers
from . import address_parser, map_service, speech_generator

FIELDS = [
    "person_name", "birth_year", "death_date", "death_time", "age",
    "visitation_date", "visitation_time", "funeral_date", "funeral_time", "address",
]

_PROMPT = (
    "Bạn đọc ảnh một tờ CÁO PHÓ (tin buồn) tiếng Việt, có thể viết tay. "
    "Trả về DUY NHẤT một đối tượng JSON (không markdown, không giải thích) với các khoá:\n"
    "person_name (tên người mất), birth_year (năm sinh), "
    "death_date (ngày mất dạng dd/mm/yyyy), death_time (giờ mất dạng HH:MM), "
    "age (hưởng thọ, chỉ số), "
    "visitation_date, visitation_time (lễ viếng), funeral_date, funeral_time (lễ truy điệu/đưa tang), "
    "address (ĐỊA CHỈ tổ chức tang lễ hoặc an táng: ghép số nhà, ngách, ngõ, đường, phường/xã, quận/huyện, thành phố — "
    "chỉ ghép phần ĐỌC ĐƯỢC, KHÔNG suy diễn), "
    "full_text (TOÀN BỘ chữ đọc được, mỗi dòng một dòng, giữ nguyên số), "
    "speech_text (một đoạn văn TỰ NHIÊN trang trọng để đọc to như lời cáo phó; "
    "VIẾT SỐ THÀNH CHỮ, ví dụ 1952 -> 'một nghìn chín trăm năm mươi hai'; không đọc máy móc từng dòng). "
    "Thiếu thông tin nào để chuỗi rỗng \"\". TUYỆT ĐỐI không bịa."
)


def _parse_json(s: str) -> dict:
    s = (s or "").strip()
    # bỏ rào ```json nếu có
    s = re.sub(r"^```(json)?", "", s).strip()
    s = re.sub(r"```$", "", s).strip()
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)  # lấy khối {...} đầu tiên
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}


def extract_obituary(image_bytes: bytes) -> dict:
    raw = vision_complete(image_bytes, _PROMPT, max_tokens=2048)
    data = _parse_json(raw)

    out = {k: str(data.get(k) or "").strip() for k in FIELDS}
    out["address"] = address_parser.clean(out["address"])
    out["map_url"] = map_service.maps_url(out["address"])

    # speech_text: ưu tiên của AI; thiếu -> fallback ghép từ trường.
    speech = str(data.get("speech_text") or "").strip()
    out["speech_text"] = speech or speech_generator.build_speech(out)
    out["audio_url"] = ""  # MP3 sinh theo yêu cầu qua POST /tts (FE gọi khi bấm Tải MP3)

    # lottery_numbers: từ full_text, dùng parser số hiện tại (2 số cuối + dedupe ở FE).
    full_text = str(data.get("full_text") or "")
    lines = [OCRResult(text=ln, confidence=0.9, bbox=[]) for ln in full_text.splitlines() if ln.strip()]
    out["lottery_numbers"] = [asdict(n) for n in extract_numbers(lines)]

    return out
