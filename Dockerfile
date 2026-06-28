# Always-on worker: continuously polls the inbox and replies (no GitHub cron).
FROM python:3.11-slim

WORKDIR /app

# Install Python deps first (layer cache), then the matching Chromium + its system libs.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

COPY . .
RUN pip install --no-cache-dir -e .

ENV HEADLESS=true \
    PYTHONUNBUFFERED=1

# `worker` (no --once) runs the poll loop forever, polling every POLL_INTERVAL_SEC.
CMD ["python", "-m", "regulatory_agent", "worker"]
