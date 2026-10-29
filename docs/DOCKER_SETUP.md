# ShadowOps — Containerized Environment Setup Guide (Docker)

## 1. Overview

The ShadowOps Docker configuration encapsulates the entire full-stack cybersecurity SaaS platform into a standardized, reproducible container containing:
- **Node.js**: `v24.19.0` (with `npm` and `npx`)
- **Python**: `3.15.0` (compiled CPython runtime with `pip`)
- **Supabase CLI**: Official Supabase binary and npm command-line tool
- **Firebase CLI**: Global `firebase-tools`
- **Semgrep Scanner**: Static security analysis engine
- **FastAPI Backend**: Python asynchronous REST API (port `8000`)
- **Next.js 14 Frontend**: Modern React dashboard (port `3000`)

---

## 2. Quick Start with Docker

### 2.1 Build the Docker Image
```bash
docker build -t shadowops:latest .
```

### 2.2 Run the Entire Platform
To start both the Backend (port 8000) and Frontend (port 3000):
```bash
docker run -it --rm -p 8000:8000 -p 3000:3000 shadowops:latest
```
Access the application:
- **Frontend Dashboard**: `http://localhost:3000`
- **Backend API Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/v1/health`

---

## 3. Quick Start with Docker Compose

### 3.1 Start Unified Platform
```bash
docker compose up --build
```

### 3.2 Start in Development Mode (Live Reloading)
```bash
docker compose --profile dev up --build
```
This mounts local `./backend` and `./frontend` directories into the container for instant hot-reloading when modifying code.

### 3.3 Start with Local PostgreSQL Database
```bash
docker compose --profile db up -d postgres
```

---

## 4. Environment & CLI Execution Modes

The container's `entrypoint.sh` supports multiple operational modes:

| Command | Description |
|---|---|
| `docker run -it shadowops:latest start` | Starts production Backend and Frontend concurrently (Default). |
| `docker run -it shadowops:latest dev` | Starts Backend with `--reload` and Frontend with `next dev`. |
| `docker run -it -p 8000:8000 shadowops:latest backend` | Starts only the FastAPI backend server. |
| `docker run -it -p 3000:3000 shadowops:latest frontend` | Starts only the Next.js frontend server. |
| `docker run -it shadowops:latest test` | Executes the full 83-test pytest test suite. |
| `docker run -it shadowops:latest bash` | Launches interactive shell with all CLI tools loaded. |

### 4.1 Verifying Installed Tooling inside the Container
Run an interactive bash session:
```bash
docker run -it --rm shadowops:latest bash
```
Verify the versions:
```bash
node -v          # v24.19.0
python --version # Python 3.15.0
supabase --version
firebase --version
semgrep --version
```

### 4.2 Running Database & Firebase Commands
- **Run Supabase Migrations**:
  ```bash
  docker run -it --rm shadowops:latest supabase db push
  ```
- **Login to Firebase**:
  ```bash
  docker run -it --rm shadowops:latest firebase login --no-localhost
  ```

---

## 5. Network Ports

| Port | Service | Description |
|---|---|---|
| `8000` | FastAPI | Backend REST API & OpenAPI docs (`/docs`) |
| `3000` | Next.js | Web Application & Executive Dashboard |
| `54321` | Supabase Gateway | Local Supabase API proxy |
| `54322` | Supabase DB | Local PostgreSQL connection port |
| `54323` | Supabase Studio | Local database web UI |
| `9099` | Firebase Emulator | Local Firebase Authentication emulator |
