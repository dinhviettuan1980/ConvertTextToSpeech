"""
Nhận diện TỔNG QUÁT 1 ảnh bất kỳ rồi trích/suy số phù hợp -> JSON chuẩn.

Không còn giới hạn "chỉ cáo phó": 1 lần gọi Groq vừa PHÂN LOẠI ảnh (cáo phó / biển số xe /
văn bản có số / cảnh vật không chữ số) vừa trích luôn thông tin theo loại đó (tiết kiệm gọi —
chỉ cáo phó mới cần chống ảo giác nghiêm ngặt bằng nhiều lần gọi, xem obituary.py).

Nếu phân loại ra CÁO PHÓ -> chuyển hẳn qua obituary.extract_obituary() (gọi 2-3 lần độc lập +
bỏ phiếu, đã có sẵn).

Nếu ảnh KHÔNG có chữ/số đọc được (người, con vật, cây...) -> vẫn trả "numbers" bằng cách ĐẾM
đối tượng nổi bật (số người, số cây...) và dùng số đếm làm gợi ý — suy đoán mang tính giải trí
kiểu "giải mã hình ảnh" (giống cầu Ông Phong/Pascal đã có), KHÔNG phải OCR thật nên luôn gắn
source="guess" để FE hiển thị khác với số OCR thật (source="ocr").
"""
from __future__ import annotations

import re
import json
from dataclasses import asdict

from .groq_engine import vision_complete
from .base import OCRResult
from .parser import extract_numbers
from . import obituary as obituary_mod

TYPES = ("obituary", "license_plate", "document", "scene", "unknown")

_PROMPT = (
    "Bạn phân tích MỘT ảnh bất kỳ (có thể là cáo phó/tin buồn, biển số xe, giấy tờ/văn bản/hoá "
    "đơn có chữ số, hoặc cảnh vật như người/con vật/cây cối KHÔNG có chữ số rõ ràng). "
    "Trả về DUY NHẤT một đối tượng JSON (không markdown, không giải thích) với các khoá:\n"
    "image_type: một trong \"obituary\" (cáo phó/tin buồn), \"license_plate\" (biển số xe), "
    "\"document\" (văn bản/giấy tờ/hoá đơn có chữ số khác cáo phó/biển số), \"scene\" (ảnh "
    "người/con vật/cây cối/đồ vật KHÔNG có chữ số nào để đọc), \"unknown\" (không xác định được).\n"
    "plate_number (CHỈ điền khi image_type=license_plate: biển số xe đọc được, giữ nguyên định dạng).\n"
    "full_text (CHỈ điền khi ảnh có chữ/số đọc được: TOÀN BỘ chữ/số đọc được, mỗi dòng một dòng, "
    "giữ nguyên số; để chuỗi rỗng nếu ảnh không có chữ nào).\n"
    "scene_description (CHỈ điền khi image_type=scene: mô tả ngắn, vd '4 người đứng trước cổng').\n"
    "object_counts (CHỈ điền khi image_type=scene: mảng JSON các đối tượng nổi bật ĐẾM ĐƯỢC, vd "
    "[{\"label\":\"người\",\"count\":4},{\"label\":\"cây\",\"count\":1}] — chỉ đếm cái thấy rõ, "
    "KHÔNG đoán bừa; không đếm được gì thì để mảng rỗng []).\n"
    "speech_text (một câu ngắn tự nhiên mô tả/đọc nội dung ảnh; số viết thành chữ, vd 30 -> 'ba mươi').\n"
    "Trường nào thiếu/không áp dụng thì để rỗng (\"\" hoặc []). TUYỆT ĐỐI không bịa."
)


def _parse_json(s: str) -> dict:
    s = (s or "").strip()
    s = re.sub(r"^```(json)?", "", s).strip()
    s = re.sub(r"```$", "", s).strip()
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}


def _numbers_from_text(full_text: str) -> list[dict]:
    lines = [OCRResult(text=ln, confidence=0.9, bbox=[]) for ln in full_text.splitlines() if ln.strip()]
    return [{**asdict(n), "source": "ocr"} for n in extract_numbers(lines)]


def _numbers_from_counts(object_counts) -> list[dict]:
    """Mỗi đối tượng đếm được -> 1 gợi ý số (2 chữ số). Mang tính vui/suy đoán, KHÔNG phải OCR
    thật -> luôn gắn source="guess" để FE phân biệt rõ."""
    out = []
    for item in object_counts or []:
        if not isinstance(item, dict):
            continue
        try:
            count = int(item.get("count"))
        except (TypeError, ValueError):
            continue
        if count <= 0:
            continue
        label = str(item.get("label") or "").strip() or "đối tượng"
        value = f"{count:02d}" if count < 100 else str(count)
        out.append({
            "value": value, "type": "guess", "bbox": [], "confidence": 0.3,
            "context": f"đếm {label}: {count}", "source": "guess",
        })
    return out


def analyze_image(image_bytes: bytes) -> dict:
    raw = vision_complete(image_bytes, _PROMPT, max_tokens=2048)
    data = _parse_json(raw)
    image_type = str(data.get("image_type") or "unknown").strip().lower()
    if image_type not in TYPES:
        image_type = "unknown"

    if image_type == "obituary":
        out = obituary_mod.extract_obituary(image_bytes)
        out["image_type"] = "obituary"
        out["numbers"] = [{**n, "source": "ocr"} for n in out.pop("lottery_numbers", [])]
        return out

    full_text = str(data.get("full_text") or "")
    out = {
        "image_type": image_type,
        "plate_number": str(data.get("plate_number") or "").strip(),
        "scene_description": str(data.get("scene_description") or "").strip(),
        "full_text": full_text,
        "speech_text": str(data.get("speech_text") or "").strip(),
        "low_confidence": False,
        "audio_url": "",
    }
    numbers = _numbers_from_text(full_text)
    if image_type == "scene" and not numbers:
        numbers = _numbers_from_counts(data.get("object_counts"))
    out["numbers"] = numbers
    return out
