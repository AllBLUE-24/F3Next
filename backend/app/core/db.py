import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings
from shared.models.core import Base, Client, Project, ProjectStatus
from shared.models.hooks import Hook
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load from the root .env
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

# Create Async Engine
if not DATABASE_URL:
    raise ValueError(f"❌ DATABASE_URL is None! Checked at: {env_path}")

engine = create_async_engine(DATABASE_URL, echo=True)

# Create Session Factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Dependency for API Routes
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session