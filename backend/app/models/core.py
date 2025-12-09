import enum
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID, ENUM as PG_ENUM # <--- USE THIS SPECIFIC IMPORT
from sqlalchemy.sql import func
from app.core.db import Base
import uuid

# 1. Define Enum with Lowercase values
class ProjectStatus(str, enum.Enum):
    CREATED = "created"
    DISCOVERY_COMPLETE = "discovery_complete"
    TEMPLATES_READY = "templates_ready"
    UPLOADED = "uploaded"
    VALIDATED = "validated"

class Client(Base):
    __tablename__ = "clients"
    
    id = Column(String, primary_key=True) 
    email = Column(String, unique=True, nullable=True) 
    full_name = Column(String, nullable=True)          
    role = Column(String, nullable=True)               
    company_name = Column(String, nullable=True)       
    status = Column(String, server_default="active")   
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False)
    company_name = Column(String, nullable=True)
    
    # 2. Use PG_ENUM specifically
    status = Column(
        Enum(
            ProjectStatus, 
            name="project_status", 
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj] # <--- MAGIC LINE
        ), 
        nullable=False, 
        default=ProjectStatus.CREATED,
        server_default="created"
    )
    
    plan = Column(String, nullable=True)
    transaction_id = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())