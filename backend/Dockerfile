FROM python:3.13-slim

# System tools for full ingestion support (OCR + video/audio)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary

COPY . .

ENV UPLOAD_DIR=/tmp/uploads
RUN mkdir -p /tmp/uploads

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
