import os
import sys
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Ensure test environment variables are set before app imports
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["FIREBASE_PROJECT_ID"] = "shadow-ops-test"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-testing-32-chars-long"

import app.models  # Register models with Base.metadata
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def auth_headers_owner():
    return {"Authorization": "Bearer test-token-owner-user-123"}


@pytest.fixture
def auth_headers_member():
    return {"Authorization": "Bearer test-token-member-user-456"}


@pytest.fixture
def auth_headers_other():
    return {"Authorization": "Bearer test-token-unauthorized-user-789"}


@pytest.fixture
def auth_headers():
    def _create(uid: str, email: str, name: str = "Test User"):
        return {"Authorization": f"Bearer test-token-{uid}"}
    return _create
