#!/bin/bash
set -e

# Print environment banner
echo "=========================================================="
echo "  SHADOWOPS DEFENSE PLATFORM - CONTAINER ENVIRONMENT"
echo "=========================================================="
echo "  Node.js:      $(node -v 2>/dev/null || echo 'Not found')"
echo "  Python:       $(python --version 2>/dev/null || echo 'Not found')"
echo "  Supabase CLI: $(supabase --version 2>/dev/null || echo 'Installed')"
echo "  Firebase CLI: $(firebase --version 2>/dev/null || echo 'Installed')"
echo "  Semgrep:      $(semgrep --version 2>/dev/null || echo 'Installed')"
echo "=========================================================="

export PYTHONPATH="/app/backend:${PYTHONPATH}"

# Check database initialization if running SQLite or empty DB
if [ -z "$DATABASE_URL" ] || [[ "$DATABASE_URL" == *"sqlite"* ]]; then
    echo ">> Synchronizing database schema and tables..."
    python /app/create_tables.py 2>/dev/null || true
fi

# Execute mode
case "$1" in
    "backend")
        echo ">> Starting FastAPI Backend server on 0.0.0.0:8000..."
        exec uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port 8000 --reload
        ;;
    "frontend")
        echo ">> Starting Next.js Frontend server on 0.0.0.0:3000..."
        cd /app/frontend && exec npm start
        ;;
    "dev")
        echo ">> Starting ShadowOps Full Stack in Live Development Mode..."
        uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port 8000 --reload &
        BACKEND_PID=$!
        cd /app/frontend && npm run dev -- -H 0.0.0.0 -p 3000 &
        FRONTEND_PID=$!
        trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM
        wait
        ;;
    "test")
        echo ">> Executing full 83-test pytest suite..."
        cd /app && exec python -m pytest backend/tests -v
        ;;
    "start")
        echo ">> Starting ShadowOps Production Stack (FastAPI: 8000, Next.js: 3000)..."
        uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port 8000 &
        BACKEND_PID=$!
        cd /app/frontend && npm start &
        FRONTEND_PID=$!
        trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM
        wait
        ;;
    *)
        # Passthrough custom command (e.g. bash, pytest, supabase, firebase)
        exec "$@"
        ;;
esac
