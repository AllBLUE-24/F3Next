from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
USE_SQLITE = os.getenv("USE_SQLITE", "true").lower() in ("true", "1", "yes")

# Default to SQLite when no PostgreSQL (no Docker required)
if not DATABASE_URL or USE_SQLITE:
    _root = Path(__file__).resolve().parent.parent.parent
    _db_path = _root / "f3next.db"
    DATABASE_URL = f"sqlite+aiosqlite:///{_db_path}"

engine = create_async_engine(
    DATABASE_URL,
    echo=False, # Turn to False in production
    pool_pre_ping=True, 
    # UPDATE: We added the cache disable settings to the Postgres fallback
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    },
)

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_shared_db():
    async with AsyncSessionLocal() as session:
        yield session