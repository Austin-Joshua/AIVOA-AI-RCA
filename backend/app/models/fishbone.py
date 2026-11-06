from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class FishboneCause(Base):
    __tablename__ = "fishbone_causes"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    category = Column(String(50), nullable=False)  # MAN, MACHINE, MATERIAL, METHOD, MEASUREMENT, MILIEU
    cause_description = Column(String(500), nullable=False)
    status = Column(String(50), default="HYPOTHESIS")  # HYPOTHESIS, VERIFIED, RULED_OUT
    rationale = Column(Text, nullable=True)
    evidence_reference = Column(String(255), nullable=True)
    
    is_ai_suggested = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verified_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)

    promoted_to_root_cause_id = Column(Integer, ForeignKey("root_causes.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    investigation = relationship("Investigation", back_populates="fishbone_causes")
    evidence_links = relationship("FishboneEvidenceLink", back_populates="fishbone_cause", cascade="all, delete-orphan", lazy="selectin")
    verified_by_user = relationship("User", foreign_keys=[verified_by_user_id])
    promoted_to_root_cause = relationship("RootCause", foreign_keys=[promoted_to_root_cause_id])


class FishboneEvidenceLink(Base):
    __tablename__ = "fishbone_evidence_links"

    id = Column(Integer, primary_key=True, index=True)
    fishbone_cause_id = Column(Integer, ForeignKey("fishbone_causes.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False, index=True)
    
    relationship_type = Column(String(50), nullable=False, default="SUPPORTING")  # SUPPORTING, CONTRADICTORY
    relevance_explanation = Column(Text, nullable=True)
    confidence_rating = Column(String(20), default="HIGH")  # HIGH, MEDIUM, LOW
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("fishbone_cause_id", "evidence_id", "relationship_type", name="uq_fishbone_evidence_rel"),
    )

    # Relationships
    fishbone_cause = relationship("FishboneCause", back_populates="evidence_links")
    evidence = relationship("Evidence", back_populates="fishbone_links", lazy="selectin")
