# Vanessa Cloud Backend - Dockerfile
FROM python:3.12-slim

# System prerequisites
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY pyproject.toml /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi>=0.115.0 \
    uvicorn[standard]>=0.31.0 \
    aiohttp>=3.9.0 \
    google-genai>=0.1.1 \
    pydantic>=2.7.0 \
    python-dotenv>=1.0.0 \
    requests>=2.31.0 \
    websockets>=12.0

# Copy application source code
COPY . /app

# Expose cloud server port
EXPOSE 8765

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8765/api/v1/omni/status || exit 1

# Launch High-Performance Vanessa Cloud Server
CMD ["python", "server_cloud.py"]
