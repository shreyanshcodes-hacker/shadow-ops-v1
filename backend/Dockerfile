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

# Create persistent scan workspace directory
RUN mkdir -p /scan-workspace && chmod 777 /scan-workspace

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
