import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

import app.models
from app.db.base import Base
from app.db.session import engine

async def init_tables():
    print("Creating all missing tables in shadowops.db...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables synchronized successfully!")

if __name__ == "__main__":
    asyncio.run(init_tables())
