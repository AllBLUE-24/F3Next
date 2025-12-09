# schemas/models/clients.py
from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TEXT
from sqlalchemy.orm import relationship
from .base import Base, ReprMixin
import uuid

class Client(Base, ReprMixin):
    __tablename__ = "clients"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    email = sa.Column(sa.String(320), nullable=False, unique=True, index=True)
    company_name = sa.Column(sa.String(255), nullable=True)
    contact_person = sa.Column(sa.String(255), nullable=True)
    phone = sa.Column(sa.String(50), nullable=True)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False)

    projects = relationship("Project", back_populates="client", cascade="all,delete", lazy="selectin")

    __repr_keys__ = ("id", "email", "company_name")
