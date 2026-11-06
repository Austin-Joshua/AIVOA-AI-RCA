from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(Integer, primary_key=True, index=True)
    investigation_number = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(50), default="IN_INVESTIGATION")  # DRAFT, IN_INVESTIGATION, PENDING_QA_REVIEW, APPROVED, REJECTED
    stage = Column(String(50), default="INTAKE")  # INTAKE, INVESTIGATION, ROOT_CAUSE, CAPA, APPROVAL
    
    lead_investigator = Column(String(100), default="Lead Investigator")
    lead_investigator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    qa_approver = Column(String(100), nullable=True)
    qa_approver_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    is_approved = Column(Boolean, default=False)
    approval_date = Column(DateTime, nullable=True)
    approval_comments = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead_investigator_user = relationship("User", foreign_keys=[lead_investigator_id], backref="assigned_investigations")
    qa_approver_user = relationship("User", foreign_keys=[qa_approver_id], backref="approved_investigations")
    deviation = relationship("Deviation", back_populates="investigation", uselist=False, cascade="all, delete-orphan")
    evidences = relationship("Evidence", back_populates="investigation", cascade="all, delete-orphan")
    evidence_gaps = relationship("EvidenceGap", back_populates="investigation", cascade="all, delete-orphan")
    findings = relationship("InvestigationFinding", back_populates="investigation", cascade="all, delete-orphan")
    five_whys = relationship("FiveWhysStep", back_populates="investigation", cascade="all, delete-orphan", order_by="FiveWhysStep.step_number")
    fishbone_causes = relationship("FishboneCause", back_populates="investigation", cascade="all, delete-orphan")
    root_causes = relationship("RootCause", back_populates="investigation", cascade="all, delete-orphan")
    capa_actions = relationship("CapaAction", back_populates="investigation", cascade="all, delete-orphan")
    ai_interactions = relationship("AiInteraction", back_populates="investigation", cascade="all, delete-orphan")
    copilot_messages = relationship("CopilotMessage", back_populates="investigation", cascade="all, delete-orphan", order_by="CopilotMessage.created_at.asc()")
    audit_logs = relationship("AuditLog", back_populates="investigation", cascade="all, delete-orphan", order_by="AuditLog.timestamp.desc()")

