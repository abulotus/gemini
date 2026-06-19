FROM python:3.11-slim

# Install Java runtime (required by zxing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre \
    && rm -rf /var/lib/apt/lists/*

# FIX: Change WORKDIR so it does not conflict with your 'app' folder name
WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all project files into /workspace
COPY . .

EXPOSE 8000

# Run uvicorn looking for the 'app' directory inside /workspace
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
