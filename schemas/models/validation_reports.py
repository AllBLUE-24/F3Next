# schemas/models/validation_reports.py
from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, INTEGER
from sqlalchemy.orm import relationship
from .base import Base, ReprMixin

class ValidationReport(Base, ReprMixin):
    __tablename__ = "validation_reports"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    upload_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, unique=True)
    error_count = sa.Column(INTEGER, nullable=False, default=0)
    warning_count = sa.Column(INTEGER, nullable=False, default=0)
    total_records = sa.Column(INTEGER, nullable=True)
    errors = sa.Column(JSONB, nullable=True)   # [{row, column, error, value}]
    warnings = sa.Column(JSONB, nullable=True)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False)

    upload = relationship("Upload", back_populates="validation_report", lazy="joined")

    __repr_keys__ = ("id", "upload_id", "error_count")
