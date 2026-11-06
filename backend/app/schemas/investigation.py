from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.schemas.deviation import DeviationRead
from app.schemas.evidence import EvidenceRead, FindingRead, EvidenceGapRead
from app.schemas.five_whys import FiveWhysStepRead
from app.schemas.fishbone import FishboneCauseRead
from app.schemas.root_cause import RootCauseRead
from app.schemas.capa import CapaActionRead

class AuditLogRead(BaseModel):
    id: int
    user_name: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    change_summary: str
    timestamp: datetime

    class Config:
        from_attributes = True

class InvestigationBase(BaseModel):
    title: str = Field(..., example="Deviation in Batch B2026-API-044 Temperature Excursion")
    status: str = Field(default="IN_INVESTIGATION")
    stage: str = Field(default="INTAKE")
    lead_investigator: Optional[str] = "Lead Investigator"
    qa_approver: Optional[str] = None

class InvestigationCreate(InvestigationBase):
    investigation_number: Optional[str] = None

class InvestigationUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    stage: Optional[str] = None
    lead_investigator: Optional[str] = None
    qa_approver: Optional[str] = None
    is_approved: Optional[bool] = None
    approval_comments: Optional[str] = None

class InvestigationAssignOwner(BaseModel):
    new_investigator_id: int = Field(..., description="Target User ID to assign as lead investigator")
    reason: str = Field(..., min_length=10, description="Mandatory GMP rationale for ownership assignment (minimum 10 characters)")

    @field_validator("reason")
    @classmethod
    def validate_reason_non_empty(cls, v: str) -> str:
        cleaned = (v or "").strip()
        if not cleaned or len(cleaned) < 10:
            raise ValueError("Assignment reason must contain at least 10 non-whitespace characters.")
        return cleaned

class InvestigationSummary(BaseModel):
    id: int
    investigation_number: str
    title: str
    status: str
    stage: str
    lead_investigator: Optional[str]
    lead_investigator_id: Optional[int] = None
    qa_approver_id: Optional[int] = None
    is_approved: bool
    created_at: datetime
    updated_at: datetime
    deviation_number: Optional[str] = None
    batch_number: Optional[str] = None
    product_name: Optional[str] = None
    severity: Optional[str] = None

    class Config:
        from_attributes = True

class InvestigationRead(InvestigationBase):
    id: int
    investigation_number: str
    lead_investigator_id: Optional[int] = None
    qa_approver_id: Optional[int] = None
    is_approved: bool
    approval_date: Optional[datetime] = None
    approval_comments: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    deviation: Optional[DeviationRead] = None
    evidences: List[EvidenceRead] = []
    evidence_gaps: List[EvidenceGapRead] = []
    findings: List[FindingRead] = []
    five_whys: List[FiveWhysStepRead] = []
    fishbone_causes: List[FishboneCauseRead] = []
    root_causes: List[RootCauseRead] = []
    capa_actions: List[CapaActionRead] = []
    audit_logs: List[AuditLogRead] = []

    class Config:
        from_attributes = True

