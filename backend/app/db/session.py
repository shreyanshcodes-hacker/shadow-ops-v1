from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings
from app.core.logging import logger


def get_async_database_url(url: str) -> str:
    """Normalize database connection string to asyncpg for async SQLAlchemy."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


db_url = get_async_database_url(settings.DATABASE_URL)

engine = create_async_engine(
    db_url,
    echo=settings.DEBUG and not settings.is_production,
    poolclass=NullPool if settings.is_production else None,
    pool_pre_ping=True,
)

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
    """Dispose engine connections on shutdown."""
    await engine.dispose()
