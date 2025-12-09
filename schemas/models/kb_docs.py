# schemas/models/kb_docs.py
from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TEXT
from sqlalchemy.orm import relationship
from .base import Base, ReprMixin

class KBDoc(Base, ReprMixin):
    __tablename__ = "kb_docs"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    title = sa.Column(sa.Text, nullable=False)
    metadata = sa.Column(JSONB, nullable=True)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False)

    chunks = relationship("KBChunk", back_populates="doc", cascade="all,delete", lazy="selectin")

    __repr_keys__ = ("id", "title")