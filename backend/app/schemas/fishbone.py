from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.schemas.evidence import EvidenceRead

class FishboneEvidenceLinkBase(BaseModel):
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

class FishboneEvidenceLinkCreate(FishboneEvidenceLinkBase):
    pass

class FishboneEvidenceLinkRead(FishboneEvidenceLinkBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fishbone_cause_id: int
    created_at: datetime
    evidence: Optional[EvidenceRead] = None

class FishbonePromoteRequest(BaseModel):
    is_primary: bool = False
    category: Optional[str] = None
    investigator_notes: Optional[str] = None

class FishboneVerifyRequest(BaseModel):
    status: str = Field(default="VERIFIED")  # VERIFIED, RULED_OUT, HYPOTHESIS
    verification_notes: Optional[str] = None

class FishboneCauseBase(BaseModel):
    category: str = Field(..., example="MACHINE")  # MAN, MACHINE, MATERIAL, METHOD, MEASUREMENT, MILIEU
    cause_description: str
    status: str = Field(default="HYPOTHESIS", example="HYPOTHESIS")  # HYPOTHESIS, VERIFIED, RULED_OUT
    rationale: Optional[str] = None
    evidence_reference: Optional[str] = None
    is_ai_suggested: bool = True
    is_verified: bool = False

class FishboneCauseCreate(FishboneCauseBase):
    pass

class FishboneCauseUpdate(BaseModel):
    category: Optional[str] = None
    cause_description: Optional[str] = None
    status: Optional[str] = None
    rationale: Optional[str] = None
    evidence_reference: Optional[str] = None
    is_ai_suggested: Optional[bool] = None
    is_verified: Optional[bool] = None
    verification_notes: Optional[str] = None

class FishboneCauseRead(FishboneCauseBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    investigation_id: int
    promoted_to_root_cause_id: Optional[int] = None
    verified_by_user_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    evidence_links: List[FishboneEvidenceLinkRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None
