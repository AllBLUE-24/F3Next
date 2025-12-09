# schemas/models/projects.py
from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import Base, ReprMixin

project_status = sa.Enum(
    "created",
    "discovery_complete",
    "templates_ready",
    "uploaded",
    "validated",
    name="project_status",
)

class Project(Base, ReprMixin):
    __tablename__ = "projects"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    client_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    status = sa.Column(project_status, nullable=False, server_default="'created'")
    intake_data = sa.Column(JSONB, nullable=True)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False)
    updated_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False)

    client = relationship("Client", back_populates="projects", lazy="joined")
    recommendations = relationship("Recommendation", back_populates="project", cascade="all,delete", lazy="selectin")
    templates = relationship("Template", back_populates="project", cascade="all,delete", lazy="selectin")
    uploads = relationship("Upload", back_populates="project", cascade="all,delete", lazy="selectin")

    __repr_keys__ = ("id", "client_id", "status")
