import asyncio
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.config import settings
from app.db.session import engine
from app.db.base import Base
import app.models  # Register all models with Base.metadata

async def init_database():
    print(f"Connecting to database: {settings.DATABASE_URL}")
    async with engine.begin() as conn:
        print("Creating all database tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_database())
