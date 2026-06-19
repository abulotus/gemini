FROM python:3.11-slim

# Install system dependencies (JRE for ZXing, and core runtimes required by Paddle/OpenCV)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
