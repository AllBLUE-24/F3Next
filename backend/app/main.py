
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health_check import router as health_router
from app.api.auth import router as auth_router

# Import models to ensure tables are registered for creating
from shared.models.core import Client, Project, ProjectStatus
from shared.models.hooks import Hook
from app.core.db import engine, Base
from app.api.discovery import router as discovery_router
from app.api.onboarding import router as onboarding_router
from app.api.resolver import router as resolver_router
from app.api.config import router as config_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Logic ---
    print("🚀 App starting: Verifying database tables...")
    async with engine.begin() as conn:
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables verified/created.")
    yield  

app = FastAPI(lifespan=lifespan)

_all_models = [Base, Client, Project, ProjectStatus, Hook]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "https://f3next.vercel.app",        # Your Vercel Project URL
    "https://www.f3next.in",  
    "https://f3next.in",
    "https://f3-next-tool1-checked-git-main-parths-projects-1f4d4d4a.vercel.app",
    "https://f3-next-tool1-checked-jv1yf8emx-parths-projects-1f4d4d4a.vercel.app"
    
    ]
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Routes
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(discovery_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api")
app.include_router(resolver_router, prefix="/api")
app.include_router(config_router, prefix="/api")