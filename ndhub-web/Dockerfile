# --- Stage 1: Build React frontend ---
FROM node:20.14-slim AS frontend-build

WORKDIR /frontend
COPY frontend-react/package*.json ./
RUN npm ci
COPY frontend-react/ ./
RUN npm run build

# --- Stage 2: Python runtime image ---
FROM python:3.12.4-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Security: create unprivileged app user and group
RUN groupadd --system appgroup && useradd --system --no-create-home --gid appgroup appuser

# Install Python dependencies. Build tools are removed immediately after pip install.
COPY requirements.txt /app/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libjpeg62-turbo \
        zlib1g \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy application and frontend build artifacts.
# Secrets/DBs stay out of the context via .dockerignore (Issue #105).
COPY . /app
COPY --from=frontend-build /backend/web/react /app/backend/web/react

# Create data directories and hand ownership to app user
RUN mkdir -p /data/uploads /data/backups \
    && chown -R appuser:appgroup /app /data

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
