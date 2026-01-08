from sqlalchemy import Column, ForeignKey, Text, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from shared.database.db import Base

class ProjectAnswer(Base):
    __tablename__ = "project_answers"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relationships
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(Text, ForeignKey("node_bank.node_id", ondelete="CASCADE"), nullable=False)

    # Metadata
    user_role = Column(Text, nullable=True) # e.g. "Config_Admin"

    # Data Payloads
    answer_value = Column(JSONB, nullable=False)     # The user's input (e.g. "FIFO")
    tags_injected = Column(JSONB, nullable=True)     # Tags this answer created (e.g. ["#Inv_Batch"])
    payload_impact = Column(JSONB, nullable=True)    # The config generated (e.g. { "valuation": "FIFO" })
    
    # The Final Output (Only filled for the final summary row, or progressively)
    processed_config = Column(JSONB, nullable=True)

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