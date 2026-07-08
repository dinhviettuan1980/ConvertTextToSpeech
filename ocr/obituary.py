"""
Trích thông tin CÁO PHÓ từ ảnh bằng Groq vision -> JSON chuẩn (spec).

1 lần gọi Groq trả về các trường + full_text + speech_text. Sau đó:
  - address  -> map_service.maps_url
  - full_text -> parser.extract_numbers  -> lottery_numbers (giữ logic số hiện tại)
  - speech_text rỗng -> speech_generator (fallback)

KHÔNG bịa: trường thiếu để chuỗi rỗng.

Chống ảo giác (model đôi khi bịa nguyên 1 bộ dữ liệu KHÁC hoàn toàn, tự nhất quán —
so full_text với chính data trong CÙNG 1 lần gọi không phát hiện được vì cả 2 đều do
model bịa ra cùng lúc): gọi Groq 2 LẦN ĐỘC LẬP trên cùng ảnh, so sánh birth_year +
person_name. Khớp nhau -> tin dùng. Lệch nhau -> gọi lần 3, lấy kết quả đa số (2/3);
nếu cả 3 lần đều khác nhau thì trả kết quả lần cuối kèm cờ `low_confidence: true`
để FE có thể cảnh báo thay vì hiển thị y như chắc chắn đúng.
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
    "visitation_date", "visitation_time", "funeral_date", "funeral_time",
    "home_address", "address", "burial_address",
]

_PROMPT = (
    "Bạn đọc ảnh một tờ CÁO PHÓ (tin buồn) tiếng Việt, có thể viết tay. "
    "Trả về DUY NHẤT một đối tượng JSON (không markdown, không giải thích) với các khoá:\n"
    "person_name (tên người mất), birth_year (năm sinh), "
    "death_date (ngày mất dạng dd/mm/yyyy), death_time (giờ mất dạng HH:MM), "
    "age (hưởng thọ, chỉ số), "
    "visitation_date, visitation_time (lễ viếng), funeral_date, funeral_time (lễ truy điệu/đưa tang), "
    "home_address (ĐỊA CHỈ nhà/nơi ở của người mất hoặc gia đình — thường sau chữ 'Chỗ ở:' hoặc "
    "'Trú quán:', KHÁC với nơi tổ chức tang lễ), "
    "address (ĐỊA CHỈ TỔ CHỨC LỄ VIẾNG/LỄ TRUY ĐIỆU — thường sau chữ 'Tại:', vd nhà tang lễ: "
    "ghép số nhà, ngách, ngõ, đường, phường/xã, quận/huyện, thành phố), "
    "burial_address (ĐỊA ĐIỂM AN TÁNG/HỎA TÁNG — thường sau chữ 'Táng tại:' hoặc 'An táng tại:', "
    "THƯỜNG LÀ NƠI KHÁC với address ở trên, vd nghĩa trang/thôn/xã/tỉnh khác — để riêng, KHÔNG gộp "
    "chung với address), "
    "(cả 3 địa chỉ home_address/address/burial_address LÀ 3 NƠI KHÁC NHAU, chỉ ghép phần ĐỌC ĐƯỢC, "
    "KHÔNG suy diễn, KHÔNG lấy nhầm nơi này gán cho nơi kia, thiếu thì để rỗng), "
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


def _call_once(image_bytes: bytes) -> dict:
    raw = vision_complete(image_bytes, _PROMPT, max_tokens=2048)
    return _parse_json(raw)


def _signature(data: dict) -> tuple:
    """Fingerprint thô để so 2 lần gọi có đang mô tả CÙNG 1 cáo phó không."""
    name = re.sub(r"\s+", " ", str(data.get("person_name") or "").strip().lower())
    return (str(data.get("birth_year") or "").strip(), name[:24])


def _vote(candidates: list[dict]) -> tuple[dict, bool]:
    """Trả (data được chọn, low_confidence). 2/3 khớp -> chọn cặp khớp. Cả 3 khác nhau
    -> chọn lần cuối, đánh dấu low_confidence."""
    sigs = [_signature(c) for c in candidates]
    for i in range(len(candidates)):
        if sigs.count(sigs[i]) >= 2:
            return candidates[i], False
    return candidates[-1], True


def extract_obituary(image_bytes: bytes) -> dict:
    first = _call_once(image_bytes)
    second = _call_once(image_bytes)
    if _signature(first) == _signature(second):
        data, low_confidence = first, False
    else:
        third = _call_once(image_bytes)
        data, low_confidence = _vote([first, second, third])

    out = {k: str(data.get(k) or "").strip() for k in FIELDS}
    out["low_confidence"] = low_confidence
    out["home_address"] = address_parser.clean(out["home_address"])
    out["address"] = address_parser.clean(out["address"])
    out["map_url"] = map_service.maps_url(out["address"])
    out["burial_address"] = address_parser.clean(out["burial_address"])
    out["burial_map_url"] = map_service.maps_url(out["burial_address"])

    # speech_text: ưu tiên của AI; thiếu -> fallback ghép từ trường.
    speech = str(data.get("speech_text") or "").strip()
    out["speech_text"] = speech or speech_generator.build_speech(out)
    out["audio_url"] = ""  # MP3 sinh theo yêu cầu qua POST /tts (FE gọi khi bấm Tải MP3)

    # lottery_numbers: từ full_text, dùng parser số hiện tại (2 số cuối + dedupe ở FE).
    full_text = str(data.get("full_text") or "")
    lines = [OCRResult(text=ln, confidence=0.9, bbox=[]) for ln in full_text.splitlines() if ln.strip()]
    out["lottery_numbers"] = [asdict(n) for n in extract_numbers(lines)]

    return out
