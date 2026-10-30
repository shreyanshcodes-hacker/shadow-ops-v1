# ==============================================================================
# SHADOWOPS — FASTAPI BACKEND CONTAINER (GOOGLE CLOUD RUN)
# Optimized Python container with Semgrep SAST & Supabase PostgreSQL support
# ==============================================================================

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

# Install system dependencies & Semgrep SAST engine
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    curl \
    && pip install --no-cache-dir semgrep \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . /app/

# Create persistent scan workspace directory and non-root application user
RUN mkdir -p /scan-workspace \
    && groupadd -g 1000 appgroup \
    && useradd -u 1000 -g appgroup -s /bin/bash -m appuser \
    && chown -R appuser:appgroup /app /scan-workspace \
    && chmod 775 /scan-workspace

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
