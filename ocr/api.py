"""
FastAPI service OCR trích số.

Chạy:
  uvicorn ocr.api:app --host 0.0.0.0 --port 8020
  (từ thư mục gốc repo ConvertTextToSpeech)

Endpoints:
  GET  /health        -> {"ok": true, "engine": "paddle"}
  POST /ocr           -> multipart/form-data field 'file' (hoặc 'image') -> {"numbers": [...]}
"""
from __future__ import annotations

import os
from dataclasses import asdict

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .paddle_engine import create_engine
from .parser import extract_numbers

_INDEX_HTML = os.path.join(os.path.dirname(__file__), "index.html")

app = FastAPI(title="OCR Number Extractor", version="1.0.0")

# Cho FE (web khác origin) upload trực tiếp.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo engine 1 lần, dùng lại cho mọi request (model nặng).
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


@app.get("/", response_class=HTMLResponse)
def index():
    """Trang FE demo: upload ảnh, vẽ bbox, liệt kê số theo loại."""
    try:
        with open(_INDEX_HTML, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>OCR service</h1><p>POST /ocr (multipart 'file').</p>")


@app.get("/health")
def health():
    return {"ok": True, "engine": create_engine().name}


@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(..., description="Ảnh cần OCR")):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="File rỗng")
    try:
        ocr_results = get_engine().ocr(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR lỗi: {e}")

    numbers = extract_numbers(ocr_results)
    # Trả JSON đúng spec: { numbers: [ {value,type,bbox,confidence,context}, ... ] }
    return {"numbers": [asdict(n) for n in numbers]}
