"""
Trích ĐƠN THUỐC và CHỈ SỐ XÉT NGHIỆM từ ảnh bằng Groq vision (đọc cả chữ viết tay).
Dùng cho app connectdoctor: /prescription (thuốc) và /labtest (chỉ số).
KHÔNG bịa — thiếu thì để rỗng / mảng rỗng.
"""
from __future__ import annotations

import re
import json

from .groq_engine import vision_complete


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


_PRESC_PROMPT = (
    "Bạn đọc ảnh ĐƠN THUỐC tiếng Việt (có thể viết tay). "
    "Trả về DUY NHẤT một JSON (không markdown, không giải thích):\n"
    '{"meds":[{"name":"tên thuốc kèm hàm lượng","dose":"cách dùng/liều, ví dụ \'1 viên/sáng\' '
    'hoặc \'ngày 2 lần, mỗi lần 1 viên\'","quantity":"số lượng","unit":"đơn vị: viên/gói/ống...",'
    '"category":"nhóm bệnh nếu suy ra RÕ (Huyết áp/Tiểu đường/Tim mạch/Xương khớp/Tiêu hoá...), '
    'không chắc để rỗng"}],'
    '"patient_name":"","age":"","gender":"","diagnosis":"chẩn đoán","date":"ngày kê đơn",'
    '"doctor":"bác sĩ","hospital":"bệnh viện/phòng khám"}. '
    "Đọc ĐÚNG tên thuốc và số lượng, KHÔNG bịa. Thiếu thông tin để chuỗi rỗng \"\"."
)

_LAB_PROMPT = (
    "Bạn đọc ảnh KẾT QUẢ XÉT NGHIỆM hoặc chỉ số sức khoẻ (huyết áp, đường huyết, mỡ máu, công thức máu...). "
    "Trả về DUY NHẤT một JSON (không markdown):\n"
    '{"metrics":[{"label":"tên chỉ số","value":"giá trị (giữ nguyên số)","unit":"đơn vị",'
    '"reference":"khoảng tham chiếu nếu có","type":"blood_test|blood_pressure|cholesterol|glucose|other"}]}. '
    "GIỮ NGUYÊN con số, KHÔNG bịa. Nếu ảnh không phải xét nghiệm thì trả \"metrics\":[]."
)


def extract_prescription(image_bytes: bytes) -> dict:
    d = _parse_json(vision_complete(image_bytes, _PRESC_PROMPT, max_tokens=2048))
    meds = []
    for m in (d.get("meds") or []):
        name = str(m.get("name") or "").strip()
        if not name:
            continue
        meds.append({
            "name": name,
            "dose": str(m.get("dose") or "").strip(),
            "quantity": str(m.get("quantity") or "").strip(),
            "unit": str(m.get("unit") or "").strip(),
            "category": str(m.get("category") or "").strip(),
        })
    return {
        "meds": meds,
        "patient_name": str(d.get("patient_name") or "").strip(),
        "age": str(d.get("age") or "").strip(),
        "gender": str(d.get("gender") or "").strip(),
        "diagnosis": str(d.get("diagnosis") or "").strip(),
        "date": str(d.get("date") or "").strip(),
        "doctor": str(d.get("doctor") or "").strip(),
        "hospital": str(d.get("hospital") or "").strip(),
    }


def extract_labtest(image_bytes: bytes) -> dict:
    d = _parse_json(vision_complete(image_bytes, _LAB_PROMPT, max_tokens=2048))
    metrics = []
    for m in (d.get("metrics") or []):
        label = str(m.get("label") or "").strip()
        if not label:
            continue
        metrics.append({
            "label": label,
            "value": str(m.get("value") or "").strip(),
            "unit": str(m.get("unit") or "").strip(),
            "reference": str(m.get("reference") or "").strip(),
            "type": (str(m.get("type") or "other").strip() or "other"),
        })
    return {"metrics": metrics}
