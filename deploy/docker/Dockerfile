FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV SIMULATION_PORT=9876

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libegl1 \
    libvulkan1 \
    mesa-vulkan-drivers \
    && rm -rf /var/lib/apt/lists/*

COPY deploy/docker/simulation_server.py /app/simulation_server.py

EXPOSE 9876

CMD ["python", "/app/simulation_server.py"]
