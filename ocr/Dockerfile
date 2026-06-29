# OCR number-extractor service (PaddleOCR + FastAPI, CPU).
# Build từ THƯ MỤC GỐC repo:  docker build -f ocr/Dockerfile -t ocr-numbers .
# Run:                        docker run -p 8020:8020 ocr-numbers
FROM python:3.10-slim

# Thư viện hệ thống cho opencv/paddle (libGL, glib, gomp).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ocr/requirements.txt ./ocr/requirements.txt
RUN pip install --no-cache-dir -r ocr/requirements.txt

COPY ocr/ ./ocr/

# Cổng 8020 (đổi sang 7860 nếu deploy Hugging Face Space).
EXPOSE 8020
CMD ["uvicorn", "ocr.api:app", "--host", "0.0.0.0", "--port", "8020"]
