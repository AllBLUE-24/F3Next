# schemas/models/templates.py
from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TEXT
from sqlalchemy.orm import relationship
from .base import Base, ReprMixin

class Template(Base, ReprMixin):
    __tablename__ = "templates"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    project_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    template_name = sa.Column(sa.Text, nullable=False)
    s3_url = sa.Column(sa.Text, nullable=True)
    schema = sa.Column(JSONB, nullable=True)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False)

    project = relationship("Project", back_populates="templates", lazy="joined")
    uploads = relationship("Upload", back_populates="template", cascade="all,delete", lazy="selectin")

    __repr_keys__ = ("id", "template_name")
