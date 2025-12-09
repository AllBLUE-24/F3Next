# schemas/models/recommendations.py
from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TEXT
from sqlalchemy.orm import relationship
from .base import Base, ReprMixin

class Recommendation(Base, ReprMixin):
    __tablename__ = "recommendations"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    project_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    erp_choice = sa.Column(sa.Text, nullable=False)
    confidence_score = sa.Column(sa.Float, nullable=True)
    reasoning = sa.Column(sa.Text, nullable=True)
    modules = sa.Column(JSONB, nullable=True)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False)

    project = relationship("Project", back_populates="recommendations", lazy="joined")

    __repr_keys__ = ("id", "project_id", "erp_choice")
