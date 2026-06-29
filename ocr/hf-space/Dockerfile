# OCR number-extractor — Hugging Face Space (Docker SDK), PaddleOCR CPU, cổng 7860.
# Space repo layout (do deploy_space.py dựng): Dockerfile, README.md, requirements.txt, ocr/<package>
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV OCR_LANG=vi \
    HOME=/app

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ocr/ ./ocr/

# Warm model: tải sẵn det/rec/cls vào image -> request đầu không phải tải mạng (nhanh + ổn định).
RUN python -c "from paddleocr import PaddleOCR; import numpy as np; \
o=PaddleOCR(use_angle_cls=True, lang='vi', use_gpu=False, show_log=False); \
o.ocr(np.zeros((48,48,3),dtype='uint8'), cls=True); print('paddle warmed')" || true

EXPOSE 7860
CMD ["uvicorn", "ocr.api:app", "--host", "0.0.0.0", "--port", "7860"]
