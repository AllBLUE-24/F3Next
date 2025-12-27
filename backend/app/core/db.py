from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from shared.models.core import Base, Client, Project, ProjectStatus
from shared.models.hooks import Hook
# Create Async Engine
engine = create_async_engine(settings.DATABASE_URL, echo=True)

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