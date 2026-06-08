import enum
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, Text, Index, text
from sqlalchemy.types import Uuid, JSON
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

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    processed_config = Column(JSON, nullable=True)
    deployment_details = Column(JSON, nullable=True)
    context_tags = Column(JSON, nullable=True, default=[])
    implementation_profile = Column(JSON, nullable=True)  # F3iche, industry, company context (versioned)

    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "idx_projects_deployed",
            "id",
            "company_slug",
            postgresql_where=text("deployment_details IS NOT NULL"),
        ),
    )


class ProjectMember(Base):
    """Links invited users to an existing company workspace (shared project)."""
    __tablename__ = "project_members"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False, unique=True, index=True)
    role = Column(String, nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="members")


class TeamInvite(Base):
    __tablename__ = "team_invites"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    invite_code = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String, nullable=True)
    invited_by = Column(String, ForeignKey("clients.id"), nullable=False)
    status = Column(String, server_default="pending", nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())