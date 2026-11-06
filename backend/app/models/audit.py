from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class AiInteraction(Base):
    __tablename__ = "ai_interactions"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False)
    
    interaction_type = Column(String(50), nullable=False)  # INTAKE_EXTRACTION, FIVE_WHYS, FISHBONE, CAPA, COPILOT_CHAT
    prompt_summary = Column(Text, nullable=True)
    response_data = Column(Text, nullable=True)  # JSON or text response
    model_name = Column(String(100), default="llama-3.3-70b-versatile")
    tokens_used = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="ai_interactions")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    user_name = Column(String(100), default="Investigator")
    action = Column(String(50), nullable=False)  # CREATED, FIELD_UPDATED, AI_APPLIED, VERIFIED, APPROVED, REJECTED
    entity_type = Column(String(50), nullable=False)  # DEVIATION, FIVE_WHYS, FISHBONE, ROOT_CAUSE, CAPA, INVESTIGATION
    entity_id = Column(String(50), nullable=True)
    change_summary = Column(Text, nullable=False)
    
    timestamp = Column(DateTime, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="audit_logs")
    user = relationship("User", backref="audit_logs")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=True)
    role = Column(String(50), default="INVESTIGATOR")  # INVESTIGATOR, QA_APPROVER, ADMIN
    department = Column(String(100), default="Quality Assurance")
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

