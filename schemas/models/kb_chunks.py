# schemas/models/kb_chunks.py
from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TEXT, FLOAT, JSONB
from sqlalchemy.orm import relationship
from .base import Base, ReprMixin

class KBChunk(Base, ReprMixin):
    __tablename__ = "kb_chunks"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    doc_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("kb_docs.id", ondelete="CASCADE"), nullable=False, index=True)
    content = sa.Column(TEXT, nullable=False)
    embedding = sa.Column(JSONB, nullable=True)  # storing vector as array if desired or store in vector DB
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False)

    doc = relationship("KBDoc", back_populates="chunks", lazy="joined")

    __repr_keys__ = ("id", "doc_id")