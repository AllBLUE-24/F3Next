# schemas/models/uploads.py
from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, BIGINT
from sqlalchemy.orm import relationship
from .base import Base, ReprMixin

upload_status = sa.Enum(
    "uploaded",
    "validating",
    "validated",
    "failed",
    name="upload_status",
)

class Upload(Base, ReprMixin):
    __tablename__ = "uploads"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    project_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("templates.id", ondelete="SET NULL"), nullable=True)
    filename = sa.Column(sa.Text, nullable=False)
    s3_url = sa.Column(sa.Text, nullable=True)
    file_size = sa.Column(BIGINT, nullable=True)
    status = sa.Column(upload_status, nullable=False, server_default="'uploaded'")
    uploaded_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False)

    project = relationship("Project", back_populates="uploads", lazy="joined")
    template = relationship("Template", back_populates="uploads", lazy="joined")
    validation_report = relationship("ValidationReport", back_populates="upload", uselist=False, cascade="all,delete", lazy="selectin")

    __repr_keys__ = ("id", "project_id", "filename", "status")
