from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Deviation(Base):
    __tablename__ = "deviations"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    deviation_number = Column(String(50), index=True, nullable=False)
    deviation_number_source = Column(String(20), default="SOURCE", nullable=False)  # SOURCE, SYSTEM
    deviation_type = Column(String(50), default="MAJOR")  # CRITICAL, MAJOR, MINOR
    severity = Column(String(50), default="High")
    
    # Manufacturing context
    batch_number = Column(String(100), index=True, nullable=False)
    product_name = Column(String(200), nullable=False)
    unit_operation = Column(String(100), nullable=True)  # Crystallization, Filtration, Drying, Reaction
    equipment_id = Column(String(100), nullable=True)     # e.g. RX-201, CENT-102
    bpr_number = Column(String(100), nullable=True)       # Batch Production Record
    
    target_yield_kg = Column(Float, nullable=True)
    actual_yield_kg = Column(Float, nullable=True)
    
    occurrence_datetime = Column(DateTime, nullable=True)
    detection_datetime = Column(DateTime, nullable=True)
    
    description = Column(Text, nullable=False)
    immediate_containment = Column(Text, nullable=True)
    
    # Verification flags
    is_ai_populated = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="deviation")

