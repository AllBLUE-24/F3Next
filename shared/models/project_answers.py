from sqlalchemy import Column, ForeignKey, Text, DateTime, Index, UniqueConstraint
from sqlalchemy.types import Uuid, JSON
from sqlalchemy.sql import func
import uuid
from shared.database.db import Base

class ProjectAnswer(Base):
    __tablename__ = "project_answers"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(Text, ForeignKey("node_bank.node_id", ondelete="CASCADE"), nullable=False)

    # Metadata
    user_role = Column(Text, nullable=True) # e.g. "Config_Admin"

    # Data Payloads
    answer_value = Column(JSON, nullable=False)
    tags_injected = Column(JSON, nullable=True)
    payload_impact = Column(JSON, nullable=True)
    processed_config = Column(JSON, nullable=True)

    # Timestamps
    answered_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Constraints & Indexes (Matching your image)
    __table_args__ = (
        UniqueConstraint('project_id', 'node_id', name='uq_project_node'),
        Index('idx_project_answers_project', 'project_id'),
    )

    def __repr__(self):
        return f"<ProjectAnswer(project={self.project_id}, node={self.node_id}, answer={self.answer_value})>"