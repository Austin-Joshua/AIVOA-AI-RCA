from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Evidence(Base):
    __tablename__ = "evidences"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String(200), nullable=False)
    original_filename = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    file_hash_sha256 = Column(String(64), nullable=True)
    
    evidence_type = Column(String(50), default="DOCUMENT")  # BATCH_RECORD, SCADA_TREND, LAB_HPLC, LOGBOOK, CALIBRATION_CERT, INTERVIEW, SOP, EMAIL
    classification = Column(String(50), default="PRIMARY_SOURCE")  # PRIMARY_SOURCE, ANALYTICAL_DATA, SYSTEM_TELEMETRY, TESTIMONIAL, REGULATORY_STANDARD
    source = Column(String(255), nullable=True)  # File name, system name, sensor tag
    source_location = Column(String(100), nullable=True)  # Page number, section, timestamp range
    page_number = Column(Integer, nullable=True)
    extracted_text = Column(Text, nullable=True)
    source_metadata = Column(JSON, nullable=True)  # Structured metadata (headers, sensor tags, etc.)
    
    confidence_score = Column(Float, default=1.0)
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String(100), nullable=True)
    verified_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    verification_date = Column(DateTime, nullable=True)
    investigator_notes = Column(Text, nullable=True)

    # Uploader attribution for segregation of duties
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Soft Archival / Retention (cGMP Compliance)
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    archived_at = Column(DateTime, nullable=True)
    archived_by = Column(String(100), nullable=True)
    archival_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    investigation = relationship("Investigation", back_populates="evidences")
    uploaded_by_user = relationship("User", foreign_keys=[uploaded_by_user_id])
    verified_by_user = relationship("User", foreign_keys=[verified_by_user_id])
    root_cause_links = relationship("RootCauseEvidenceLink", back_populates="evidence", cascade="all, delete-orphan")
    five_whys_links = relationship("FiveWhysEvidenceLink", back_populates="evidence", cascade="all, delete-orphan")
    fishbone_links = relationship("FishboneEvidenceLink", back_populates="evidence", cascade="all, delete-orphan")
    resolving_gaps = relationship("EvidenceGap", foreign_keys="EvidenceGap.resolving_evidence_id", back_populates="resolving_evidence")

class InvestigationFinding(Base):
    __tablename__ = "investigation_findings"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidences.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    finding_text = Column(Text, nullable=False)
    finding_type = Column(String(50), default="FACT")  # FACT, OBSERVATION, TIMELINE, GAP, INCONSISTENCY
    evidence_reference = Column(String(255), nullable=True)
    source_location = Column(String(100), nullable=True)
    
    is_ai_suggested = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    citation_verified = Column(Boolean, default=False, nullable=False)
    validation_status = Column(String(50), nullable=True, default="UNVERIFIED")  # VERIFIED_SOURCE_FACT, UNVERIFIED_CITATION, PARAPHRASED_OBSERVATION
    
    is_accepted = Column(Boolean, default=False, nullable=False)
    user_edited = Column(Boolean, default=False, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    original_finding_text = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="findings")
    evidence = relationship("Evidence", backref="findings")
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by_id], backref="reviewed_findings")

class EvidenceGap(Base):
    __tablename__ = "evidence_gaps"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    root_cause_id = Column(Integer, ForeignKey("root_causes.id", ondelete="SET NULL"), nullable=True, index=True)
    
    category = Column(String(100), nullable=False)  # CALIBRATION_RECORDS, RAW_MATERIAL_COA, OPERATOR_LOGS, SCADA_TELEMETRY, SOP_PROCEDURE
    question = Column(Text, nullable=False)
    impact_description = Column(Text, nullable=False)
    suggested_record = Column(String(255), nullable=True)
    urgency = Column(String(20), default="HIGH")  # HIGH, MEDIUM, LOW
    
    investigator_response = Column(Text, nullable=True)
    response_timestamp = Column(DateTime, nullable=True)
    responded_by = Column(String(100), nullable=True)
    
    is_resolved = Column(Boolean, default=False)
    resolving_evidence_id = Column(Integer, ForeignKey("evidences.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    investigation = relationship("Investigation", back_populates="evidence_gaps")
    root_cause = relationship("RootCause", back_populates="linked_gaps")
    resolving_evidence = relationship("Evidence", foreign_keys=[resolving_evidence_id], back_populates="resolving_gaps")
