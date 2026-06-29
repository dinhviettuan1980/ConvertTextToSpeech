---
title: OCR Numbers
emoji: 🔢
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# OCR Numbers — trích tất cả con số trong ảnh (PaddleOCR, CPU)

Service FastAPI đọc ảnh tiếng Việt và trả về mọi chuỗi số kèm `type`, `bbox`, `confidence`.

- `GET  /`        → trang demo upload (FE).
- `GET  /health`  → `{ ok, engine }`.
- `POST /ocr`     → multipart field `file` → `{ numbers: [...] }`.

Source/tài liệu: repo `ConvertTextToSpeech/ocr/`. Deploy bằng `ocr/hf-space/deploy_space.py`.
