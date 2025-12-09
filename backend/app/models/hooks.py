from sqlalchemy import Column, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.db import Base
import uuid

class Hook(Base):
    __tablename__ = "hooks"

    # 'id' is uuid in the image
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # project_id is uuid
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Only this specific jsonb column exists in the image
    answers_health_check = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())