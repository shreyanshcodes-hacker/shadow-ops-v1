import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.api.v1.api import api_router
from app.security.firebase import init_firebase
from app.db.session import close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info(
        "shadowops_backend_starting",
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
    )
    init_firebase()
    yield
    # Shutdown
    logger.info("shadowops_backend_shutting_down")
    await close_db()


app = FastAPI(
    title="ShadowOps Security API",
    description="Your AI Security Team. Always Watching. — Production Backend Core API",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# CORS Middleware (Restricted to authorized origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Workspace-Id", "X-Request-Id"],
)


@app.middleware("http")
async def security_headers_and_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    start_time = time.time()

    response = await call_next(request)

    duration_ms = (time.time() - start_time) * 1000

    # Defensive Security Headers
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    logger.info(
        "http_request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
        request_id=request_id,
    )
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Defensive global exception handler:
    Logs full exception server-side while ensuring NO sensitive stack traces leak to client.
    """
    logger.error(
        "unhandled_server_exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred while processing your request.",
            "status_code": 500,
        },
    )


# Mount API V1 router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    return {
        "service": "ShadowOps Security API",
        "tagline": "Your AI Security Team. Always Watching.",
        "status": "online",
        "api_docs": f"{settings.API_V1_PREFIX}/health",
    }
