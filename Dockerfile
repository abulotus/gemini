FROM python:3.11-slim

# Install Java runtime (required by zxing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all project files into /workspace
COPY . .

EXPOSE 8000

# FIXES:
# 1. PYTHONPATH=. forces Python to look in the current folder (/workspace) for the 'app' module.
# 2. python -m uvicorn ensures it boots via the Python interpreter directly rather than the global binary.
ENV PYTHONPATH=/workspace

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
