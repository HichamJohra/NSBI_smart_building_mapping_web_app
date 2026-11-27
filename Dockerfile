# NSBI Smart Building Mapping – container image (Google Cloud Run or any Docker host)
#   docker build -t nsbi-app .
#   docker run -p 8080:8080 nsbi-app        ->  http://localhost:8080
FROM python:3.13-slim

# uv, pinned (same version as the uv-lock pre-commit hook)
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# 1. Dependencies only (cached as long as pyproject.toml and uv.lock do not change), no development tools
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --locked --no-dev --no-default-groups

# 2. The app and its dataset
COPY . .

ENV PATH="/app/.venv/bin:$PATH"

# Cloud Run provides $PORT (8080 by default). One worker process with several threads keeps the in-memory
# rate limiter of the 'Contribute data' page consistent within a container.
# SUBMISSIONS_DIR must point to persistent storage in production (see docs/deployment.md).
CMD exec gunicorn --bind :${PORT:-8080} --workers 1 --threads 8 --timeout 120 app:server
