FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY services/shared/requirements.txt /app/services/shared/requirements.txt
COPY services/api/requirements.txt /app/services/api/requirements.txt

RUN pip install --no-cache-dir -r /app/services/shared/requirements.txt \
    && pip install --no-cache-dir -r /app/services/api/requirements.txt

COPY services/shared /app/services/shared
COPY services/api /app/services/api

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "services.api.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
