from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class RootCause(Base):
    __tablename__ = "root_causes"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    cause_statement = Column(Text, nullable=False)
    category = Column(String(100), default="EQUIPMENT_FAILURE")  # SYSTEMIC, EQUIPMENT_FAILURE, RAW_MATERIAL, HUMAN_ERROR, PROCEDURE
    is_primary = Column(Boolean, default=True)  # True = Primary Root Cause, False = Contributing Factor
    status = Column(String(50), default="PROPOSED")  # PROPOSED, UNDER_REVIEW, CONFIRMED, REJECTED
    rationale = Column(Text, nullable=True)
    
    evidence_summary = Column(Text, nullable=True)
    is_ai_suggested = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    investigator_notes = Column(Text, nullable=True)
    
    # Source provenance
    source_type = Column(String(50), default="DIRECT_SYNTHESIS")  # FIVE_WHYS, FISHBONE, DIRECT_SYNTHESIS, MANUAL
    source_id = Column(Integer, nullable=True)
    
    # Human confirmation tracking
    confirmed_by = Column(String(100), nullable=True)
    confirmed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    
    # Human rejection tracking
    rejection_reason = Column(Text, nullable=True)
    rejected_by = Column(String(100), nullable=True)
    rejected_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    investigation = relationship("Investigation", back_populates="root_causes")
    capa_actions = relationship("CapaAction", back_populates="root_cause")
    evidence_links = relationship("RootCauseEvidenceLink", back_populates="root_cause", cascade="all, delete-orphan", lazy="selectin")
    dispositions = relationship("ContradictionDisposition", back_populates="root_cause", cascade="all, delete-orphan", lazy="selectin")
    linked_gaps = relationship("EvidenceGap", back_populates="root_cause")
    confirmed_by_user = relationship("User", foreign_keys=[confirmed_by_user_id])
    rejected_by_user = relationship("User", foreign_keys=[rejected_by_user_id])

class RootCauseEvidenceLink(Base):
    __tablename__ = "root_cause_evidence_links"

    id = Column(Integer, primary_key=True, index=True)
    root_cause_id = Column(Integer, ForeignKey("root_causes.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False, index=True)
    
    relationship_type = Column(String(50), nullable=False, default="SUPPORTING")  # SUPPORTING, CONTRADICTORY
    relevance_explanation = Column(Text, nullable=True)
    confidence_rating = Column(String(20), default="HIGH")  # HIGH, MEDIUM, LOW
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("root_cause_id", "evidence_id", "relationship_type", name="uq_root_cause_evidence_rel"),
    )

    # Relationships
    root_cause = relationship("RootCause", back_populates="evidence_links")
    evidence = relationship("Evidence", back_populates="root_cause_links", lazy="selectin")

class ContradictionDisposition(Base):
    __tablename__ = "contradiction_dispositions"

    id = Column(Integer, primary_key=True, index=True)
    root_cause_id = Column(Integer, ForeignKey("root_causes.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False, index=True)

    relationship_type = Column(String(50), nullable=False, default="CONTRADICTORY")
    disposition_rationale = Column(Text, nullable=False)
    dismissed_by = Column(String(100), nullable=False)
    dismissed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    dismissed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    original_link_created_at = Column(DateTime, nullable=True)
    original_relevance_explanation = Column(Text, nullable=True)

    # Relationships
    root_cause = relationship("RootCause", back_populates="dispositions")
    evidence = relationship("Evidence")
    dismissed_by_user = relationship("User")
