from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

VALID_CAPA_TYPES = {"CORRECTION", "CORRECTIVE_ACTION", "PREVENTIVE_ACTION"}
VALID_CAPA_STATUSES = {"PROPOSED", "APPROVED", "IN_PROGRESS", "COMPLETED", "EFFECTIVENESS_VERIFIED"}

class CapaActionBase(BaseModel):
    action_type: str = Field(..., example="CORRECTIVE_ACTION")
    description: str
    rationale: Optional[str] = None
    owner: Optional[str] = None
    deadline: Optional[str] = None
    effectiveness_criteria: Optional[str] = None
    effectiveness_review_period_days: int = 30
    status: str = Field(default="PROPOSED")
    is_ai_suggested: bool = False
    is_verified: bool = False
    root_cause_id: Optional[int] = None

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        clean = v.upper().strip().replace(" ", "_")
        if clean not in VALID_CAPA_TYPES:
            raise ValueError(f"Invalid CAPA action_type: {v}. Must be one of {VALID_CAPA_TYPES}")
        return clean

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        clean = v.upper().strip()
        if clean == "OPEN":
            return "PROPOSED"
        if clean == "CLOSED":
            return "COMPLETED"
        if clean not in VALID_CAPA_STATUSES:
            raise ValueError(f"Invalid CAPA status: {v}. Must be one of {VALID_CAPA_STATUSES}")
        return clean

class CapaActionCreate(BaseModel):
    action_type: str = Field(..., example="CORRECTIVE_ACTION")
    description: str
    rationale: Optional[str] = None
    owner: Optional[str] = None
    deadline: Optional[str] = None
    effectiveness_criteria: Optional[str] = None
    effectiveness_review_period_days: int = 30
    root_cause_id: Optional[int] = None
    is_ai_suggested: bool = False
    status: Optional[str] = "PROPOSED"
    is_verified: Optional[bool] = False

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        clean = v.upper().strip().replace(" ", "_")
        if clean not in VALID_CAPA_TYPES:
            raise ValueError(f"Invalid CAPA action_type: {v}. Must be one of {VALID_CAPA_TYPES}")
        return clean

class CapaActionUpdate(BaseModel):
    action_type: Optional[str] = None
    description: Optional[str] = None
    rationale: Optional[str] = None
    owner: Optional[str] = None
    deadline: Optional[str] = None
    effectiveness_criteria: Optional[str] = None
    effectiveness_review_period_days: Optional[int] = None
    status: Optional[str] = None
    is_ai_suggested: Optional[bool] = None
    is_verified: Optional[bool] = None
    root_cause_id: Optional[int] = None

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.upper().strip().replace(" ", "_")
        if clean not in VALID_CAPA_TYPES:
            raise ValueError(f"Invalid CAPA action_type: {v}. Must be one of {VALID_CAPA_TYPES}")
        return clean

class CapaApproveRequest(BaseModel):
    approval_notes: Optional[str] = None

class CapaEffectivenessVerifyRequest(BaseModel):
    verification_notes: Optional[str] = None

class CapaCompleteRequest(BaseModel):
    completion_notes: Optional[str] = None

class CapaActionRead(CapaActionBase):
    id: int
    investigation_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
