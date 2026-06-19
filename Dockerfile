# Use a lightweight official Python base image
FROM python:3.11-slim

# Install system dependencies: JRE for ZXing, Tesseract for OCR, and Arabic language data
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre \
    tesseract-ocr \
    tesseract-ocr-ara \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app

# Copy dependency definition and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files into the container
COPY . .

# Expose port 8000 for FastAPI
EXPOSE 8000

# Run the FastAPI application via uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
