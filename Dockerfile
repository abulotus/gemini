FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Fix: Change directory straight into /workspace/app and run main.py directly
WORKDIR /workspace/app
CMD ["python", "main.py"]
