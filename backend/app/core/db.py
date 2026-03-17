import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from shared.database.db import Base
from shared.models.core import Client, Project, ProjectStatus
from shared.models.hooks import Hook
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load from the root .env
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

USE_SQLITE = os.getenv("USE_SQLITE", "true").lower() in ("true", "1", "yes")
DATABASE_URL = os.getenv("DATABASE_URL")

# Use SQLite by default (no Docker/PostgreSQL required)
if USE_SQLITE or not DATABASE_URL:
    _db_path = Path(__file__).resolve().parent.parent.parent.parent / "f3next.db"
    DATABASE_URL = f"sqlite+aiosqlite:///{_db_path}"
    print(f"📁 Using SQLite: {_db_path}")

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# Create Session Factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency for API Routes
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session