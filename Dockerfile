# ==============================================================================
# SHADOWOPS — AI-NATIVE CYBERSECURITY DEFENSE PLATFORM
# Unified Dockerfile: Node.js v24.19.0, Python 3.15.0, Supabase CLI, Firebase CLI
# ==============================================================================

FROM ubuntu:24.04 AS base

LABEL maintainer="ShadowOps Security Engineering <operator@shadowops.io>"
LABEL description="Complete containerized environment with Node v24.19.0, Python 3.15.0, Supabase CLI, Firebase CLI, Semgrep, and full multi-tenant security architecture."

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# ------------------------------------------------------------------------------
# 1. System Dependencies & Build Toolchain
# ------------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    build-essential \
    ca-certificates \
    gnupg \
    libssl-dev \
    libffi-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    liblzma-dev \
    libpq-dev \
    sqlite3 \
    xz-utils \
    procps \
    net-tools \
    jq \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------------------
# 2. Python 3.15.0 Runtime Environment
# ------------------------------------------------------------------------------
ARG PYTHON_VERSION=3.15.0
RUN echo "==> Fetching and compiling Python ${PYTHON_VERSION}..." && \
    git clone --depth 1 --branch 3.15 https://github.com/python/cpython.git /tmp/cpython 2>/dev/null || \
    git clone --depth 1 https://github.com/python/cpython.git /tmp/cpython && \
    cd /tmp/cpython && \
    ./configure --prefix=/usr/local --without-tests --with-ensurepip=install && \
    make -j$(nproc) && \
    make install && \
    rm -rf /tmp/cpython && \
    ln -sf /usr/local/bin/python3 /usr/local/bin/python && \
    ln -sf /usr/local/bin/pip3 /usr/local/bin/pip && \
    python --version && pip --version

# ------------------------------------------------------------------------------
# 3. Node.js v24.19.0 Runtime Environment
# ------------------------------------------------------------------------------
ENV NODE_VERSION=24.19.0
RUN echo "==> Installing Node.js v${NODE_VERSION}..." && \
    ARCH="x64" && \
    (curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${ARCH}.tar.xz" -o /tmp/node.tar.xz 2>/dev/null || \
     curl -fsSL "https://nodejs.org/dist/latest-v24.x/node-$(curl -fsSL https://nodejs.org/dist/latest-v24.x/SHASUMS256.txt | grep linux-x64.tar.xz | head -n1 | awk '{print $2}')" -o /tmp/node.tar.xz) && \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 --no-same-owner && \
    rm -f /tmp/node.tar.xz && \
    node --version && npm --version

# ------------------------------------------------------------------------------
# 4. Firebase CLI
# ------------------------------------------------------------------------------
RUN echo "==> Installing Firebase CLI..." && \
    npm install -g firebase-tools && \
    firebase --version

# ------------------------------------------------------------------------------
# 5. Supabase CLI
# ------------------------------------------------------------------------------
RUN echo "==> Installing Supabase CLI..." && \
    curl -fsSL https://github.com/supabase/cli/releases/latest/download/supabase_linux_amd64.tar.gz | tar -xz -C /usr/local/bin && \
    chmod +x /usr/local/bin/supabase && \
    npm install -g supabase && \
    supabase --version

# ------------------------------------------------------------------------------
# 6. Semgrep Static Analysis Engine
# ------------------------------------------------------------------------------
RUN echo "==> Installing Semgrep static code analysis scanner..." && \
    pip install --no-cache-dir semgrep && \
    semgrep --version

# ------------------------------------------------------------------------------
# 7. Application Working Directory & Project Dependencies
# ------------------------------------------------------------------------------
WORKDIR /app

# Install Python backend dependencies first for Docker caching
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Install Node.js frontend dependencies
COPY frontend/package*.json /app/frontend/
RUN cd /app/frontend && npm install

# Copy full application codebase
COPY . /app

# Compile Next.js production build
RUN cd /app/frontend && npm run build

# Make startup entrypoint executable
RUN chmod +x /app/entrypoint.sh

# ------------------------------------------------------------------------------
# 8. Network Ports & Execution Lifecycle
# ------------------------------------------------------------------------------
# 8000:  FastAPI Backend REST API
# 3000:  Next.js 14 Web Frontend
# 54321: Supabase Local Gateway
# 54322: Supabase PostgreSQL DB
# 54323: Supabase Studio Web UI
# 9099:  Firebase Auth Emulator
EXPOSE 8000 3000 54321 54322 54323 9099

ENV PYTHONPATH=/app/backend
ENV PORT=8000
ENV HOST=0.0.0.0

ENTRYPOINT ["/app/entrypoint.sh"]

# Default mode starts both Backend (8000) and Frontend (3000)
CMD ["start"]
