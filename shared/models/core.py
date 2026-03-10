import enum
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, JSON
from sqlalchemy.sql import func
from shared.database.db import Base
import uuid

# Enums
class ProjectStatus(str, enum.Enum):
    CREATED = "created"
    DISCOVERY_COMPLETE = "discovery_complete"
    CONFIG_COMPLETED = "config_completed"       # Config Agent Finished
    DEPLOYMENT_IN_PROGRESS = "deployment_in_progress" # Apply/Template Agents Running
    DEPLOYMENT_COMPLETED = "deployment_completed"     # ERPNext is Live
    TEMPLATES_READY = "templates_ready"
    UPLOADED = "uploaded"
    VALIDATED = "validated"
    INTERESTED = "interested" 
    LISTED = "listed"         

class Client(Base):
    __tablename__ = "clients"
    
    id = Column(String, primary_key=True) 
    email = Column(String, unique=True, nullable=True) 
    full_name = Column(String, nullable=True)          
    role = Column(String, nullable=True)               
    company_name = Column(String, nullable=True)       
    status = Column(String, server_default="active")   
    
    # 🔴 MOVED HERE (Matches your DB columns exactly)
    phone_no = Column(String, nullable=True)
    whatsapp_no = Column(String, nullable=True)
    silver_bullet = Column(String, nullable=True)
    comment = Column(Text, nullable=True)

    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    user_slug = Column(String, unique=True, nullable=True)

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False)
    company_name = Column(String, nullable=True)
    
    status = Column(
        Enum(
            ProjectStatus, 
            name="project_status", 
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj]
        ), 
        nullable=False, 
        default=ProjectStatus.CREATED,
        server_default="created"
    )
    
    # 🔴 KEPT HERE (Matches your DB)
    annual_bleed = Column(String, nullable=True)
    
    plan = Column(String, nullable=True)
    transaction_id = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    company_slug = Column(String, unique=True, nullable=True)
    processed_config = Column(JSONB, nullable=True)
    deployment_details = Column(JSONB, nullable=True)
    context_tags = Column(JSON, nullable=True, default=[])

    