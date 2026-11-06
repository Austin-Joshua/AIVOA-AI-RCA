from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.schemas.evidence import EvidenceRead

class RootCauseEvidenceLinkBase(BaseModel):
    evidence_id: int
    relationship_type: str = Field(default="SUPPORTING")  # SUPPORTING, CONTRADICTORY
    relevance_explanation: Optional[str] = None
    confidence_rating: Optional[str] = "HIGH"

    @field_validator("relationship_type")
    @classmethod
    def validate_rel_type(cls, v: str) -> str:
        valid_types = ["SUPPORTING", "CONTRADICTORY"]
        if v.upper() not in valid_types:
            raise ValueError(f"relationship_type must be one of {valid_types}")
        return v.upper()

class RootCauseEvidenceLinkCreate(RootCauseEvidenceLinkBase):
    pass

class RootCauseEvidenceLinkRead(RootCauseEvidenceLinkBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    root_cause_id: int
    created_at: datetime
    evidence: Optional[EvidenceRead] = None

class RootCauseConfirmRequest(BaseModel):
    investigator_name: str = Field(..., min_length=2)
    justification: str = Field(..., min_length=10, description="Scientific and empirical justification for confirming root cause")

class RootCauseRejectRequest(BaseModel):
    investigator_name: str = Field(..., min_length=2)
    rationale: str = Field(..., min_length=5, description="Rationale for rejecting proposed root cause")

class ContradictionDispositionCreate(BaseModel):
    disposition_rationale: str = Field(..., min_length=10, description="Mandatory rationale explaining why contradictory evidence is dismissed or resolved")
    investigator_name: Optional[str] = None

class ContradictionDispositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    root_cause_id: int
    evidence_id: int
    relationship_type: str = "CONTRADICTORY"
    disposition_rationale: str
    dismissed_by: str
    dismissed_by_user_id: Optional[int] = None
    dismissed_at: datetime
    original_link_created_at: Optional[datetime] = None
    original_relevance_explanation: Optional[str] = None

class RootCauseBase(BaseModel):
    cause_statement: str
    description: Optional[str] = None
    category: str = Field(default="EQUIPMENT_FAILURE")
    is_primary: bool = True
    evidence_summary: Optional[str] = None
    supporting_evidence_references: List[str] = Field(default_factory=list)
    contributing_factors: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    status: str = Field(default="PROPOSED")  # PROPOSED, UNDER_REVIEW, CONFIRMED, REJECTED
    rationale: Optional[str] = None
    is_ai_suggested: bool = True
    is_verified: bool = False
    investigator_notes: Optional[str] = None
    source_type: Optional[str] = "DIRECT_SYNTHESIS"  # FIVE_WHYS, FISHBONE, DIRECT_SYNTHESIS, MANUAL
    source_id: Optional[int] = None

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return "DIRECT_SYNTHESIS"
        allowed = {"FIVE_WHYS", "FISHBONE", "DIRECT_SYNTHESIS", "MANUAL"}
        if v.upper() not in allowed:
            raise ValueError(f"Invalid source_type '{v}'. Allowed types: {sorted(allowed)}")
        return v.upper()

    @model_validator(mode="after")
    def validate_status_safety(self) -> "RootCauseBase":
        # Regulatory safety: AI generated root causes must never be automatically CONFIRMED
        if self.is_ai_suggested and not self.is_verified:
            if self.status == "CONFIRMED":
                self.status = "PROPOSED"
        return self

class RootCauseCreate(RootCauseBase):
    pass

class RootCauseUpdate(BaseModel):
    cause_statement: Optional[str] = None
    category: Optional[str] = None
    is_primary: Optional[bool] = None
    status: Optional[str] = None
    rationale: Optional[str] = None
    evidence_summary: Optional[str] = None
    is_ai_suggested: Optional[bool] = None
    investigator_notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_update_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.upper() in ("CONFIRMED", "REJECTED"):
            raise ValueError(
                "Status cannot transition directly to CONFIRMED or REJECTED via generic update. "
                "Use formal /confirm or /reject review endpoints."
            )
        return v

class RootCauseRead(RootCauseBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    investigation_id: int
    confirmed_by: Optional[str] = None
    confirmed_by_user_id: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    rejected_by: Optional[str] = None
    rejected_by_user_id: Optional[int] = None
    rejected_at: Optional[datetime] = None
    evidence_links: List[RootCauseEvidenceLinkRead] = Field(default_factory=list)
    dispositions: List[ContradictionDispositionRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
