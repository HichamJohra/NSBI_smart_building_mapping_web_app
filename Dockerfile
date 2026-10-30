# NSBI Smart Building Mapping – container image (Google Cloud Run or any Docker host)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run provides $PORT (8080 by default). One worker process with several threads keeps the in-memory
# rate limiter of the 'Contribute data' page consistent within a container.
# SUBMISSIONS_DIR must point to persistent storage in production (see docs/deployment.md).
CMD exec gunicorn --bind :${PORT:-8080} --workers 1 --threads 8 --timeout 120 app:server
