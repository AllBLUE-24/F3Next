# schemas/clients.py
from sqlalchemy import Column, text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from .base import Base
from .mixins import TimestampMixin

class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # If you have other columns (name, email, ...) add them here.
    # example (ONLY add if you actually have it in DB): 
    # name = Column(String(255), nullable=False)

    __table_args__ = (
        # example placeholder index; remove if not needed
        # Index("ix_clients_dummy", "id"),
    )
