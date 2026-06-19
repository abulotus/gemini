FROM python:3.11-slim

# Install Java runtime (required by zxing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

EXPOSE 8000

# Run uvicorn pointing to the app directory
CMD ["sh", "-c", "uvicorn app.main:app --app-dir app --host 0.0.0.0 --port ${PORT:-8000}"]
