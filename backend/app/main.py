
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
#  from app.api.health_check import router as health_router
from app.api.auth import router as auth_router
from dotenv import load_dotenv
load_dotenv()

import os
import sentry_sdk

sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        profile_session_sample_rate=1.0,
        profile_lifecycle="trace",
        send_default_pii=True,  # captures LLM inputs/outputs
        enable_logs=True,
    )

from shared.models.core import Client, Project, ProjectStatus, ProjectMember, TeamInvite
from shared.models.hooks import Hook
from shared.models.is_models import (
    ISSession, ISFile, ISFileSignal, ISF3icheScore,
    ISCompanyProfile, ISTargetStructure, ISDataReadinessAssessment, ISFieldMapping, ISMappedData,
    ISValidationResult, ISValidationError, ISImportPlan, ISImportLog, ISAuditTrail,
)
from shared.models.cvs_models import ContextSnapshot, ContextEvent
from shared.models.notification_models import CascadeEvent, Notification
from shared.models.f3iche_models import F3icheDefinition
from shared.database.db import engine, Base
from app.api.discovery import router as discovery_router
from app.api.onboarding import router as onboarding_router
from app.api.invites import router as invites_router
from app.api.resolver import router as resolver_router
from app.api.deploy import router as deploy_router
from app.api.agents import router as agents_router
from app.api.migration import router as migration_router
from app.api.ingest import router as ingest_router
from app.api.os_command import router as os_router
from app.api.implementation import router as implementation_router
from app.api.cvs import router as cvs_router
from app.api.admin_f3iches import router as admin_f3iches_router
from app.api.target_structure import router as target_structure_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Logic ---
    print("App starting: Verifying database tables...")
    async with engine.begin() as conn:
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables verified/created.")
    yield  

app = FastAPI(lifespan=lifespan)


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    from fastapi import Response
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

_all_models = [
    Base, Client, Project, ProjectStatus, ProjectMember, TeamInvite, Hook,
    ISSession, ISFile, ISFileSignal, ISF3icheScore,
    ISCompanyProfile, ISTargetStructure, ISDataReadinessAssessment, ISFieldMapping, ISMappedData,
    ISValidationResult, ISValidationError, ISImportPlan, ISImportLog, ISAuditTrail,
    ContextSnapshot, ContextEvent, CascadeEvent, Notification, F3icheDefinition,
]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
_default_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "https://f3next.vercel.app",
    "https://www.f3next.in",
    "https://f3next.in",
    "https://f3-next-tool1-checked-git-main-parths-projects-1f4d4d4a.vercel.app",
    "https://f3-next-tool1-checked-jv1yf8emx-parths-projects-1f4d4d4a.vercel.app",
]
# Extend with any extra origins from env (comma-separated), as well as FRONTEND_URL
_extra = os.getenv("ALLOWED_ORIGINS", "")
_frontend_url = os.getenv("FRONTEND_URL", os.getenv("NEXT_PUBLIC_SITE_URL", ""))
origins = _default_origins + [o.strip() for o in _extra.split(",") if o.strip()]
if _frontend_url:
    origins.append(_frontend_url.strip())
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
# app.include_router(health_router)
app.include_router(auth_router)
app.include_router(discovery_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api")
app.include_router(invites_router, prefix="/api")
app.include_router(resolver_router, prefix="/api")
app.include_router(deploy_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(migration_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")
app.include_router(os_router, prefix="/api")
app.include_router(implementation_router, prefix="/api")
app.include_router(cvs_router, prefix="/api")
app.include_router(admin_f3iches_router, prefix="/api")
app.include_router(target_structure_router, prefix="/api")
