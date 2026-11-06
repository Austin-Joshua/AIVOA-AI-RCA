from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects import postgresql
from datetime import datetime
from app.core.database import Base

class InvestigationSearchIndex(Base):
    __tablename__ = "investigation_search_index"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False, index=True)  # EVIDENCE, FINDING, DEVIATION, FIVE_WHYS, FISHBONE, ROOT_CAUSE, GAP, CHAT
    evidence_id = Column(Integer, ForeignKey("evidences.id", ondelete="CASCADE"), nullable=True, index=True)
    page = Column(Integer, nullable=True)
    snippet = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Dialect-specific TSVECTOR for PostgreSQL full-text search
    tsv = Column(postgresql.TSVECTOR, nullable=True)

    # Relationships
    investigation = relationship("Investigation", backref="search_entries")
    evidence = relationship("Evidence", backref="search_entries")

    __table_args__ = (
        Index("ix_investigation_search_index_tsv", "tsv", postgresql_using="gin"),
        Index("ix_investigation_search_inv_type", "investigation_id", "source_type"),
    )

