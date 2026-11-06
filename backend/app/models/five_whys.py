from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class FiveWhysStep(Base):
    __tablename__ = "five_whys_steps"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    step_number = Column(Integer, nullable=False)  # Dynamic step depth (1, 2, 3, ...)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    evidence_reference = Column(String(255), nullable=True)
    
    is_ai_suggested = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verified_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    investigation = relationship("Investigation", back_populates="five_whys")
    evidence_links = relationship("FiveWhysEvidenceLink", back_populates="five_whys_step", cascade="all, delete-orphan", lazy="selectin")
    verified_by_user = relationship("User", foreign_keys=[verified_by_user_id])


class FiveWhysEvidenceLink(Base):
    __tablename__ = "five_whys_evidence_links"

    id = Column(Integer, primary_key=True, index=True)
    five_whys_step_id = Column(Integer, ForeignKey("five_whys_steps.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False, index=True)
    
    relationship_type = Column(String(50), nullable=False, default="SUPPORTING")  # SUPPORTING, CONTRADICTORY
    relevance_explanation = Column(Text, nullable=True)
    confidence_rating = Column(String(20), default="HIGH")  # HIGH, MEDIUM, LOW
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("five_whys_step_id", "evidence_id", "relationship_type", name="uq_five_whys_evidence_rel"),
    )

    # Relationships
    five_whys_step = relationship("FiveWhysStep", back_populates="evidence_links")
    evidence = relationship("Evidence", back_populates="five_whys_links", lazy="selectin")
