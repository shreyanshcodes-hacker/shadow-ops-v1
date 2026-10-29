import time
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import HealthResponse, DatabaseHealthResponse, ReadinessResponse
from app.models.notification import EventOutbox

router = APIRouter(tags=["Health & Observability"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Service liveness probe (legacy/default)."""
    return HealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version="1.0.0",
        timestamp=datetime.utcnow(),
    )


@router.get("/health/live", response_model=HealthResponse)
async def get_liveness():
    """Kubernetes/Railway Liveness Probe: Confirms HTTP process is running."""
    return HealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version="1.0.0",
        timestamp=datetime.utcnow(),
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def get_readiness(db: AsyncSession = Depends(get_db)):
    """
    Kubernetes/Railway Readiness Probe:
    Evaluates database connectivity, scanner tool availability, and event outbox queue health.
    Never exposes internal secrets or credentials.
    """
    db_status = {"connected": False, "latency_ms": None}
    start = time.time()
    try:
        res = await db.execute(text("SELECT 1"))
        if res.scalar() == 1:
            db_status["connected"] = True
            db_status["latency_ms"] = round((time.time() - start) * 1000, 2)
    except Exception as e:
        db_status["error"] = "Database connection failed"

    # Scanner tool availability
    semgrep_installed = bool(shutil.which("semgrep"))
    scanner_status = {
        "engine": "semgrep",
        "available": semgrep_installed,
        "mode": "cli" if semgrep_installed else "mock_or_container",
    }

    # Outbox backlog
    outbox_status = {"pending": 0, "quarantined": 0}
    try:
        pending_stmt = select(func.count(EventOutbox.id)).where(EventOutbox.status == "pending")
        quarantined_stmt = select(func.count(EventOutbox.id)).where(EventOutbox.status == "quarantined")
        outbox_status["pending"] = (await db.execute(pending_stmt)).scalar() or 0
        outbox_status["quarantined"] = (await db.execute(quarantined_stmt)).scalar() or 0
    except Exception:
        pass

    is_ready = db_status["connected"]
    return ReadinessResponse(
        status="ready" if is_ready else "degraded",
        environment=settings.ENVIRONMENT,
        database=db_status,
        scanner=scanner_status,
        outbox_backlog=outbox_status,
        timestamp=datetime.utcnow(),
    )


@router.get("/health/database", response_model=DatabaseHealthResponse)
async def get_database_health(db: AsyncSession = Depends(get_db)):
    """Database probe checking database connectivity."""
    start = time.time()
    try:
        result = await db.execute(text("SELECT 1"))
        val = result.scalar()
        latency = (time.time() - start) * 1000

        if val == 1:
            return DatabaseHealthResponse(
                status="connected",
                database_connected=True,
                latency_ms=round(latency, 2),
                timestamp=datetime.utcnow(),
            )
        else:
            return DatabaseHealthResponse(
                status="degraded",
                database_connected=False,
                latency_ms=round(latency, 2),
                timestamp=datetime.utcnow(),
            )
    except Exception as e:
        latency = (time.time() - start) * 1000
        return DatabaseHealthResponse(
            status="degraded",
            database_connected=False,
            latency_ms=round(latency, 2),
            pool_info={"error": "Database unreachable"},
            timestamp=datetime.utcnow(),
        )
