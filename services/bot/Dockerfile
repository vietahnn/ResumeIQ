FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY services/shared/requirements.txt /app/services/shared/requirements.txt
COPY services/bot/requirements.txt /app/services/bot/requirements.txt

RUN pip install --no-cache-dir -r /app/services/shared/requirements.txt \
    && pip install --no-cache-dir -r /app/services/bot/requirements.txt

COPY services/shared /app/services/shared
COPY services/bot /app/services/bot

EXPOSE 8001

CMD ["uvicorn", "services.bot.src.main:app", "--host", "0.0.0.0", "--port", "8001"]
