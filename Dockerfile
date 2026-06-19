# Use a lightweight official Python base image
FROM python:3.11-slim

# Install system dependencies: JRE for ZXing, Tesseract for OCR, and Arabic language data
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre \
    tesseract-ocr \
    tesseract-ocr-ara \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /workspace

# Copy dependency definition and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything (including your local 'app' folder) into /workspace
COPY . .

# Expose port 8000 for FastAPI
EXPOSE 8000

# Tell Uvicorn to look inside the 'app' folder for 'main.py' (app.main:app)
# Change the static --port 8000 to use the environment variable $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

