from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index
from sqlalchemy.types import JSON
from sqlalchemy.sql import func, text
from shared.database.db import Base

class NodeBank(Base):
    __tablename__ = "node_bank"

    # Primary Key
    node_id = Column(Text, primary_key=True)

    # Classification Columns
    module_ref = Column(Text, nullable=False, index=True) # Indexed for fast module lookup
    target_role = Column(Text, index=True)                # Indexed for fast role lookup
    layer = Column(Integer, nullable=False, index=True)   # The new column! Indexed for sequential fetching.

    # The Payload
    node_data = Column(JSON, nullable=False)

    # Meta / Audit Columns
    version = Column(Integer, server_default=text("1"))
    is_active = Column(Boolean, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # PostgreSQL GIN index omitted for SQLite compatibility
    __table_args__ = ()

    def __repr__(self):
        return f"<NodeBank(id={self.node_id}, module={self.module_ref}, layer={self.layer})>"