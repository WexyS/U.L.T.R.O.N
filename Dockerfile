# Ultron AGI v3.0 - Backend Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy project files
COPY ultron/ ./ultron/
COPY config/ ./config/
COPY data/ ./data/

# Expose FastAPI port
EXPOSE 8000

# Start backend
CMD ["uvicorn", "ultron.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
