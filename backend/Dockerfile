ARG PYTHON_VERSION=3.12-slim-bullseye
FROM python:${PYTHON_VERSION}

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code

# Install system dependencies including a stable Java runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre \
    libpq-dev \
    libjpeg-dev \
    libcairo2 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set up virtual environment
RUN python -m venv /opt/venv \
    && pip install --no-cache-dir --upgrade pip

WORKDIR /code

# Copy requirements first to take advantage of Docker caching layers
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy your source folder contents into /code
COPY ./src /code/

# Create the startup shell script securely
RUN printf "#!/bin/bash\n\
RUN_PORT=\"\${PORT:-8000}\"\n\
exec gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:\$RUN_PORT\n" > ./paracord_runner.sh \
    && chmod +x paracord_runner.sh

# Ensure the debug uploads directory exists and has permissions
RUN mkdir -p /code/debug_uploads && chmod 777 /code/debug_uploads

CMD ["./paracord_runner.sh"]
