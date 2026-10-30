from datetime import datetime, timezone
from typing import AsyncGenerator, Optional, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.sql import sqltypes
from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg, AsyncpgDateTime
from app.core.config import settings
from app.core.logging import logger

_cloud_sql_connector: Optional[Any] = None


class SafeAsyncpgDateTime(AsyncpgDateTime):
    """
    Ensures naive UTC datetime objects (such as from datetime.utcnow()) are
    automatically tagged with timezone.utc when bound to PostgreSQL TIMESTAMPTZ
    columns via asyncpg, preventing offset-naive vs offset-aware DataErrors.
    """
    def bind_processor(self, dialect):
        def process(value):
            if isinstance(value, datetime):
                if self.timezone and value.tzinfo is None:
                    return value.replace(tzinfo=timezone.utc)
                elif not self.timezone and value.tzinfo is not None:
                    return value.astimezone(timezone.utc).replace(tzinfo=None)
            return value
        return process


PGDialect_asyncpg.colspecs = {
    **PGDialect_asyncpg.colspecs,
    sqltypes.DateTime: SafeAsyncpgDateTime,
}


def get_async_database_url(url: str) -> str:
    """Normalize database connection string to asyncpg for async SQLAlchemy."""
    url = url.strip()
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    # Clean query parameters for asyncpg compatibility (sslmode -> ssl, strip pgbouncer)
    if "?" in url:
        base, query = url.split("?", 1)
        cleaned_params = []
        for param in query.split("&"):
            if not param:
                continue
            key_lower = param.split("=", 1)[0].lower()
            if key_lower in ("pgbouncer", "prepared_statements"):
                continue
            if key_lower == "sslmode":
                val = param.split("=", 1)[1] if "=" in param else "require"
                cleaned_params.append(f"ssl={val}")
            else:
                cleaned_params.append(param)
        url = f"{base}?{'&'.join(cleaned_params)}" if cleaned_params else base
    return url


def create_engine_instance() -> AsyncEngine:
    """
    Factory creating an AsyncEngine instance.
    Supports both direct PostgreSQL/Supabase connections and Google Cloud SQL Connector.
    """
    global _cloud_sql_connector

    if settings.USE_CLOUD_SQL_CONNECTOR and settings.CLOUD_SQL_CONNECTION_NAME:
        try:
            from google.cloud.sql.connector import Connector, IPTypes
            _cloud_sql_connector = Connector()

            async def getconn():
                conn = await _cloud_sql_connector.connect_async(
                    settings.CLOUD_SQL_CONNECTION_NAME,
                    "asyncpg",
                    user=settings.CLOUD_SQL_USER,
                    password=settings.CLOUD_SQL_PASSWORD,
                    db=settings.CLOUD_SQL_DATABASE,
                    enable_iam_auth=settings.CLOUD_SQL_IAM_AUTH,
                    ip_type=IPTypes.PRIVATE if settings.is_production else IPTypes.PUBLIC,
                )
                return conn

            logger.info("initializing_cloud_sql_connector", instance=settings.CLOUD_SQL_CONNECTION_NAME)
            return create_async_engine(
                "postgresql+asyncpg://",
                async_creator=getconn,
                echo=settings.DEBUG and not settings.is_production,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_recycle=settings.DB_POOL_RECYCLE,
                pool_pre_ping=True,
            )
        except Exception as e:
            logger.error("cloud_sql_connector_init_failed_falling_back_to_url", error=str(e))

    # Fallback to standard connection URL (Supabase PostgreSQL / Local Postgres / SQLite)
    normalized_url = get_async_database_url(settings.DATABASE_URL)
    is_sqlite = normalized_url.startswith("sqlite")

    connect_args = {}
    if not is_sqlite:
        # Disable asyncpg & SQLAlchemy prepared statement caches for Supabase Supavisor/PgBouncer
        # and enforce fast connection/command timeouts to prevent 131s stale socket hangs.
        connect_args = {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "timeout": 10,
            "command_timeout": 25,
        }

    return create_async_engine(
        normalized_url,
        echo=False,
        poolclass=NullPool if not is_sqlite else None,
        connect_args=connect_args,
    )


engine = create_engine_instance()

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> bool:
    """Performs a lightweight ping check to verify database connectivity."""
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.warning("database_health_check_failed", error=str(e))
        return False


async def close_db() -> None:
    """Dispose engine connections and close Cloud SQL connector on shutdown."""
    global _cloud_sql_connector
    try:
        await engine.dispose()
        if _cloud_sql_connector:
            await _cloud_sql_connector.close_async()
            _cloud_sql_connector = None
        logger.info("database_connections_closed_cleanly")
    except Exception as e:
        logger.error("error_during_database_shutdown", error=str(e))
