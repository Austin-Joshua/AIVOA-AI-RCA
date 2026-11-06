from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.schemas.evidence import EvidenceRead

class FiveWhysEvidenceLinkBase(BaseModel):
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

class FiveWhysEvidenceLinkCreate(FiveWhysEvidenceLinkBase):
    pass

class FiveWhysEvidenceLinkRead(FiveWhysEvidenceLinkBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    five_whys_step_id: int
    created_at: datetime
    evidence: Optional[EvidenceRead] = None

class FiveWhysVerifyRequest(BaseModel):
    is_verified: bool = True
    verification_notes: Optional[str] = None

class FiveWhysStepBase(BaseModel):
    step_number: int = Field(..., ge=1)  # Dynamic depth support (no artificial <= 5 limit)
    question: str
    answer: str
    evidence_reference: Optional[str] = None
    is_ai_suggested: bool = True
    is_verified: bool = False

class FiveWhysStepCreate(FiveWhysStepBase):
    pass

class FiveWhysStepUpdate(BaseModel):
    step_number: Optional[int] = Field(None, ge=1)
    question: Optional[str] = None
    answer: Optional[str] = None
    evidence_reference: Optional[str] = None
    is_ai_suggested: Optional[bool] = None
    is_verified: Optional[bool] = None
    verification_notes: Optional[str] = None

class FiveWhysStepRead(FiveWhysStepBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    investigation_id: int
    verified_by_user_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    evidence_links: List[FiveWhysEvidenceLinkRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None
