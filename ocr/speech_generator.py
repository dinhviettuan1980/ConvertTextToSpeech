"""
Sinh đoạn văn đọc cáo phó (tự nhiên, không robot).

Mặc định AI (Gemini) đã trả `speech_text` tự nhiên (số đọc thành chữ). Module này là
FALLBACK khi thiếu speech_text: ghép một đoạn ngắn từ các trường đã nhận diện.
Không bịa — trường nào trống thì bỏ qua.
"""
from __future__ import annotations


def build_speech(f: dict) -> str:
    if not f:
        return ""
    p = []
    p.append("Cáo phó.")
    p.append("Gia đình trân trọng báo tin.")
    name = (f.get("person_name") or "").strip()
    by = (f.get("birth_year") or "").strip()
    s = name or "Người thân của chúng tôi"
    if by:
        s += f", sinh năm {by}"
    dd = (f.get("death_date") or "").strip()
    dt = (f.get("death_time") or "").strip()
    if dt or dd:
        s += ", đã từ trần"
        if dt:
            s += f" lúc {dt}"
        if dd:
            s += f" ngày {dd}"
    age = (f.get("age") or "").strip()
    if age:
        s += f", hưởng thọ {age} tuổi"
    p.append(s + ".")
    home = (f.get("home_address") or "").strip()
    if home:
        p.append(f"Chỗ ở: {home}.")
    vd = (f.get("visitation_date") or "").strip()
    if vd or f.get("visitation_time"):
        p.append(f"Lễ viếng được tổ chức {('lúc ' + f['visitation_time'] + ' ') if f.get('visitation_time') else ''}ngày {vd}.".strip())
    fd = (f.get("funeral_date") or "").strip()
    if fd or f.get("funeral_time"):
        p.append(f"Lễ truy điệu và đưa tang {('lúc ' + f['funeral_time'] + ' ') if f.get('funeral_time') else ''}ngày {fd}.".strip())
    addr = (f.get("address") or "").strip()
    if addr:
        p.append(f"Địa chỉ: {addr}.")
    burial = (f.get("burial_address") or "").strip()
    if burial:
        p.append(f"An táng tại: {burial}.")
    p.append("Gia đình kính báo.")
    return "\n".join(p)
