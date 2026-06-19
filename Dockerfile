FROM python:3.11-slim

# Install Java runtime (required by zxing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre \
    && rm -rf /var/lib/apt/lists/*

# Use a neutral workspace directory to avoid naming conflicts with the app package
WORKDIR /workspace

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . .

EXPOSE 8000

# Explicitly tell Python to include /workspace in its module search path
ENV PYTHONPATH=/workspace

# Boot the application using python's module execution system
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
