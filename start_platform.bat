@echo off
echo ========================================================
echo       Starting ShadowOps Defense Platform (Local)
echo ========================================================
echo.

echo Checking and freeing ports 8000 and 3000 if occupied...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Terminating lingering process on port 8000 (PID %%a)...
    taskkill /F /PID %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo Terminating lingering process on port 3000 (PID %%a)...
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo 1. Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "ShadowOps Backend" cmd /k "backend\venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000"

echo 2. Starting Next.js Frontend on http://localhost:3000 ...
start "ShadowOps Frontend" cmd /k "npm --prefix frontend start"

echo.
echo ========================================================
echo Platform is launching!
echo Access the dashboard: http://localhost:3000/login
echo.
echo Dummy User Credentials:
echo   Email:    operator@shadowops.io
echo   Password: Password123!
echo ========================================================
echo Opening browser in 4 seconds...
timeout /t 4 >nul
start http://localhost:3000/login
