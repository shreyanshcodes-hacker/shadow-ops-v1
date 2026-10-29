Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      Starting ShadowOps Defense Platform (Local)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 0. Check and free ports 8000 and 3000 if already occupied by stale processes
foreach ($port in @(8000, 3000)) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conns) {
        $pids = $conns.OwningProcess | Select-Object -Unique
        foreach ($pidToKill in $pids) {
            if ($pidToKill -gt 0) {
                Write-Host "Reclaiming port $port (stopping stale process PID: $pidToKill)..." -ForegroundColor Yellow
                Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

Write-Host "1. Launching Backend on http://127.0.0.1:8000..." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/k backend\venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000"

Write-Host "2. Launching Frontend on http://localhost:3000..." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/k npm --prefix frontend start"

Write-Host "`nPlatform is running!" -ForegroundColor Cyan
Write-Host "Access URL: http://localhost:3000/login" -ForegroundColor Yellow
Write-Host "Email:    operator@shadowops.io" -ForegroundColor Yellow
Write-Host "Password: Password123!" -ForegroundColor Yellow
