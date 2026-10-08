FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY services/shared/requirements.txt /app/services/shared/requirements.txt
COPY services/worker/requirements.txt /app/services/worker/requirements.txt

RUN pip install --no-cache-dir -r /app/services/shared/requirements.txt \
    && pip install --no-cache-dir -r /app/services/worker/requirements.txt

COPY services/shared /app/services/shared
COPY services/worker /app/services/worker

ENV PYTHONPATH=/app

CMD ["python", "services/worker/src/main.py"]
