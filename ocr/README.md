# OCR Number Extractor — trích TẤT CẢ con số trong ảnh (PaddleOCR + FastAPI, CPU)

Đọc ảnh tiếng Việt và trả về **mọi chuỗi chứa số** (không bỏ sót), kèm `type`, `bbox`,
`confidence`. Engine OCR **swappable** (sau thay PaddleOCR → Surya/Mistral không sửa business logic).

## Cấu trúc
```
ocr/
  base.py          # Interface BaseOCREngine + dataclass OCRResult/NumberItem (KHÔNG phụ thuộc Paddle)
  paddle_engine.py # PaddleEngine implement BaseOCREngine + factory create_engine()
  parser.py        # Trích mọi cụm số từ kết quả OCR (regex) — không bỏ sót, không sửa số
  extractor.py     # Phân loại number|date|time|address_number|phone|age|unknown
  api.py           # FastAPI: POST /ocr, GET /health
  requirements.txt
  Dockerfile
```
Luồng: `api` → `engine.ocr(bytes)` → `parser.extract_numbers()` (gọi `extractor.classify()`) → JSON.

## Chạy local
```bash
cd /Users/tuandv/ConvertTextToSpeech
python3.10 -m venv .venv && source .venv/bin/activate   # Paddle cần Python 3.8–3.12
pip install -r ocr/requirements.txt
uvicorn ocr.api:app --host 0.0.0.0 --port 8020
```
Lần gọi `/ocr` đầu tiên PaddleOCR tự tải model (det/rec/cls, ~vài trăm MB) rồi cache lại.

## Test
```bash
curl -s -X POST http://localhost:8020/ocr -F "file=@tinbuon.jpg" | jq
```

## Định dạng trả về
```json
{
  "numbers": [
    {"value":"1952","type":"number","bbox":[90,470,560,520],"confidence":0.97,"context":"Sinh năm : 1952"},
    {"value":"75","type":"age","bbox":[...],"confidence":0.96,"context":"... Thọ 75 tuổi"},
    {"value":"0987654321","type":"phone","bbox":[...],"confidence":0.98,"context":"..."},
    {"value":"27/06/2026","type":"date","bbox":[...],"confidence":0.97,"context":"..."},
    {"value":"06:22","type":"time","bbox":[...],"confidence":0.98,"context":"..."}
  ]
}
```

## Quy tắc phân loại
| type | điều kiện |
|---|---|
| `time` | `HH:MM` / `HH:MM:SS` |
| `date` | `d/m/y`, `d-m-y`, `d.m.y` |
| `phone` | `0xxxxxxxxx` hoặc `+84xxxxxxxxx` (9–11 số) |
| `age` | số 1–3 chữ số + LÂN CẬN có "thọ"/"tuổi" |
| `address_number` | số 1–3 chữ số + lân cận có "SN"/"ngõ"/"ngách"/"số nhà"/"đường"/"phố"… |
| `number` | số nguyên thuần còn lại |
| `unknown` | còn lại (vd `12A`, `193/12`) |

Nguyên tắc: **không bỏ sót** (thà thừa hơn thiếu), **giữ nguyên chuỗi OCR gốc**, **không tự sửa/suy luận**.

> Lưu ý: nếu OCR đọc giờ tách rời ("06 giờ 22") thì ra 2 số `06` và `22` (đúng theo gốc).
> Chỉ khi OCR cho chuỗi liền "06:22" mới gán `time`. Không tự ghép — tránh suy luận sai.

## Đổi engine (Surya / Mistral) sau này
Viết class mới implement `BaseOCREngine.ocr(bytes) -> List[OCRResult]`, thêm nhánh trong
`paddle_engine.create_engine()` (hoặc tách `engine_factory`), chọn qua ENV `OCR_ENGINE`.
`parser.py` / `extractor.py` / `api.py` GIỮ NGUYÊN.

## ENV
| ENV | mặc định | ý nghĩa |
|---|---|---|
| `OCR_ENGINE` | `paddle` | engine OCR |
| `OCR_LANG` | `vi` | ngôn ngữ PaddleOCR |

## Docker
```bash
docker build -f ocr/Dockerfile -t ocr-numbers .
docker run -p 8020:8020 ocr-numbers
```
Server yếu/không Docker → có thể deploy như Hugging Face Space (đổi cổng 7860) giống `kd-embed`.

## Tích hợp Frontend (upload)
```js
async function ocrImage(file) {
  const fd = new FormData();
  fd.append("file", file);                       // field 'file'
  const res = await fetch("http://localhost:8020/ocr", { method: "POST", body: fd });
  const { numbers } = await res.json();
  return numbers; // [{value,type,bbox,confidence,context}, ...]
}
// <input type="file" accept="image/*" onChange={e => ocrImage(e.target.files[0]).then(console.log)} />
```
