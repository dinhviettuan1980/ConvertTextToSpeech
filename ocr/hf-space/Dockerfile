# OCR Space (Docker, cổng 7860) — biến thể GROQ vision (nhẹ, không cần paddle/opencv).
# Đọc cả chữ viết tay. Space layout do deploy_space.py dựng: Dockerfile, README.md,
# requirements.txt (bản nhẹ), ocr/<package>.
FROM python:3.10-slim

ENV OCR_ENGINE=groq \
    HOME=/app

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ocr/ ./ocr/

EXPOSE 7860
CMD ["uvicorn", "ocr.api:app", "--host", "0.0.0.0", "--port", "7860"]
