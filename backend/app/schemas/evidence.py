from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime

class EvidenceBase(BaseModel):
    title: str
    evidence_type: str = "DOCUMENT"  # BATCH_RECORD, SCADA_TREND, LAB_HPLC, LOGBOOK, CALIBRATION_CERT, INTERVIEW, SOP, EMAIL
    classification: str = "PRIMARY_SOURCE"  # PRIMARY_SOURCE, ANALYTICAL_DATA, SYSTEM_TELEMETRY, TESTIMONIAL, REGULATORY_STANDARD
    source: Optional[str] = None
    file_path: Optional[str] = None
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    file_hash_sha256: Optional[str] = None
    source_location: Optional[str] = None
    page_number: Optional[int] = None
    extracted_text: Optional[str] = None
    source_metadata: Optional[Dict[str, Any]] = None
    confidence_score: float = 1.0
    is_verified: bool = False
    verified_by: Optional[str] = None
    verified_by_user_id: Optional[int] = None
    verification_date: Optional[datetime] = None
    investigator_notes: Optional[str] = None
    uploaded_by_user_id: Optional[int] = None
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    archived_by: Optional[str] = None
    archival_reason: Optional[str] = None
    download_url: Optional[str] = None

class EvidenceCreate(EvidenceBase):
    pass

class EvidenceUpdate(BaseModel):
    title: Optional[str] = None
    evidence_type: Optional[str] = None
    classification: Optional[str] = None
    source_location: Optional[str] = None
    page_number: Optional[int] = None
    extracted_text: Optional[str] = None  # Validated in endpoint to prevent tampering
    investigator_notes: Optional[str] = None

class EvidenceVerifyRequest(BaseModel):
    investigator_name: str = Field(..., min_length=2)
    verification_notes: Optional[str] = None

class EvidenceRead(EvidenceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    investigation_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

class FindingBase(BaseModel):
    finding_text: str
    finding_type: str = "FACT"  # FACT, OBSERVATION, TIMELINE, GAP, INCONSISTENCY
    evidence_reference: Optional[str] = None
    source_location: Optional[str] = None
    evidence_id: Optional[int] = None
    is_ai_suggested: bool = True
    is_verified: bool = False
    citation_verified: bool = False
    validation_status: Optional[str] = "UNVERIFIED"
    is_accepted: bool = False
    user_edited: bool = False
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    original_finding_text: Optional[str] = None

class FindingCreate(FindingBase):
    pass

class FindingRead(FindingBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    investigation_id: int
    created_at: datetime

# Evidence Gap Schemas
class EvidenceGapBase(BaseModel):
    category: str
    question: str
    impact_description: str
    suggested_record: Optional[str] = None
    urgency: str = "HIGH"
    root_cause_id: Optional[int] = None

class EvidenceGapCreate(EvidenceGapBase):
    pass

class EvidenceGapResponseRequest(BaseModel):
    response: str = Field(..., min_length=2)
    responder_name: str = Field(..., min_length=2)

class EvidenceGapResolveRequest(BaseModel):
    resolver_name: str = Field(..., min_length=2)
    resolving_evidence_id: Optional[int] = None
    resolution_notes: Optional[str] = None

class EvidenceGapRead(EvidenceGapBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    investigation_id: int
    investigator_response: Optional[str] = None
    response_timestamp: Optional[datetime] = None
    responded_by: Optional[str] = None
    is_resolved: bool = False
    resolving_evidence_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
