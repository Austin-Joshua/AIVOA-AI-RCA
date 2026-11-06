from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class CapaAction(Base):
    __tablename__ = "capa_actions"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False)
    root_cause_id = Column(Integer, ForeignKey("root_causes.id", ondelete="SET NULL"), nullable=True)
    
    action_type = Column(String(50), nullable=False)  # CORRECTION, CORRECTIVE_ACTION, PREVENTIVE_ACTION
    description = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)
    
    owner = Column(String(100), nullable=True)
    deadline = Column(String(50), nullable=True)  # Date or timeframe
    
    effectiveness_criteria = Column(Text, nullable=True)
    effectiveness_review_period_days = Column(Integer, default=30)
    
    status = Column(String(50), default="PROPOSED")  # PROPOSED, APPROVED, IN_PROGRESS, COMPLETED, EFFECTIVENESS_VERIFIED
    
    is_ai_suggested = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="capa_actions")
    root_cause = relationship("RootCause", back_populates="capa_actions")

