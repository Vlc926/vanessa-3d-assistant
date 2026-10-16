FROM python:3.12-slim

# System utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Setup non-root user required by Hugging Face Spaces (UID 1000)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Install dependencies
COPY --chown=user requirements.txt $HOME/app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=user . $HOME/app

USER user
EXPOSE 8765

CMD ["uvicorn", "server_cloud:app", "--host", "0.0.0.0", "--port", "8765"]
