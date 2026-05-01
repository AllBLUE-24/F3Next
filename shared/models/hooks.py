from sqlalchemy import Column, ForeignKey, DateTime, Integer, Text
from sqlalchemy.types import Uuid, JSON
from sqlalchemy.sql import func
from shared.database.db import Base
import uuid

class Hook(Base):
    __tablename__ = "hooks"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    answers_health_check = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report_content = Column(Text, nullable=True)

    last_bot_response = Column(Text, nullable=True)

    discovery_step = Column(Integer, default=1)          # kept for backward compat

    discovery_status = Column(Text, default="START")

    extracted_tags = Column(JSON, default=[])

    chat_history = Column(JSON, default=[])

    discovery_metadata = Column(JSON, nullable=True)     # f3iche, industry, price_plan from discovery

    # --- Dynamic Coverage Intelligence (v2) ---
    # Tracks what Adi has understood per dimension, independent of step count.
    # Shape: { "industry": {"status": "confirmed"|"partial"|null, "value": str|null}, ... }
    discovery_coverage = Column(JSON, nullable=True, default=None)

    # How many conversation turns have been taken (safety guardrail)
    discovery_turn_count = Column(Integer, default=0)

    

