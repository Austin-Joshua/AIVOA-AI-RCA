from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
from app.schemas.deviation import DeviationCreate
from app.schemas.five_whys import FiveWhysStepCreate
from app.schemas.fishbone import FishboneCauseCreate
from app.schemas.root_cause import RootCauseCreate
from app.schemas.capa import CapaActionCreate

class ExtractionStatus(str, Enum):
    SOURCE_FACT = "SOURCE_FACT"
    AI_INFERENCE = "AI_INFERENCE"
    MISSING = "MISSING"
    CONFLICTING = "CONFLICTING"

class ExtractedField(BaseModel):
    field_name: str = Field(..., description="Unique technical field identifier, e.g. batch_number")
    label: str = Field(..., description="Human-readable field name")
    value: Optional[str] = Field(None, description="Extracted or inferred value")
    source_reference: Optional[str] = Field(None, description="Verbatim excerpt or citation from source text")
    page_number: Optional[int] = Field(None, description="Page number where finding occurs in multi-page documents")
    source_location: Optional[str] = Field(None, description="Section, header, or offset location")
    confidence: float = Field(default=1.0, description="Confidence score between 0.0 and 1.0")
    status: ExtractionStatus = Field(default=ExtractionStatus.SOURCE_FACT, description="Fact vs Inference vs Missing vs Conflicting")
    is_accepted: bool = Field(default=False, description="Whether investigator accepted this field for application")
    user_edited: bool = Field(default=False, description="Whether investigator modified the extracted value")
    original_value: Optional[str] = Field(None, description="Original extracted value before user modification")
    reviewed_by_id: Optional[int] = Field(None, description="User ID of investigator who reviewed this field")
    reviewed_at: Optional[datetime] = Field(None, description="Timestamp of investigator review")
    validation_explanation: Optional[str] = Field(None, description="Detailed explanation from runtime citation validator")

class ConflictingInfoItem(BaseModel):
    field_name: str
    claim_a: str
    source_a: Optional[str] = None
    claim_b: str
    source_b: Optional[str] = None
    explanation: str

class MissingInfoItem(BaseModel):
    category: str  # e.g., "CALIBRATION", "RAW_MATERIAL", "BATCH_RECORD", "ENVIRONMENTAL"
    question: str
    impact_description: str
    urgency: str = "HIGH"  # HIGH, MEDIUM, LOW

class IntakeExtractionResponse(BaseModel):
    investigation_title: str
    deviation: DeviationCreate
    extracted_fields: List[ExtractedField] = []
    extracted_findings: List[Any] = []
    missing_information: List[MissingInfoItem] = []
    conflicting_information: List[ConflictingInfoItem] = []
    recommended_immediate_actions: List[str] = []
    raw_document_preview: Optional[str] = None
    source_type: str = "PDF"  # PDF, TEXT, EMAIL
    source_metadata: Optional[Dict[str, Any]] = None
    ai_confidence_score: float = 0.95

class CopilotChatRequest(BaseModel):
    investigation_id: int
    message: str = Field(..., max_length=2000, description="Investigator chat question (max 2,000 characters)")
    context_stage: Optional[str] = "INTAKE"  # INTAKE, INVESTIGATION, ROOT_CAUSE, CAPA, APPROVAL

class CopilotChatResponse(BaseModel):
    response: str
    suggested_actions: List[str] = []
    sources: Optional[List[Dict[str, Any]]] = None
    workflow_state: Optional[Dict[str, Any]] = None

class GenerateRcaRequest(BaseModel):
    investigation_id: int
    user_context: Optional[str] = None

class RcaAnalysisResult(BaseModel):
    five_whys: List[FiveWhysStepCreate] = []
    fishbone_causes: List[FishboneCauseCreate] = []
    root_causes: List[RootCauseCreate] = []
    capa_actions: List[CapaActionCreate] = []
    evidence_gaps: List[str] = []
    investigator_guidance: str = ""
    status: str = "SUCCESS"  # SUCCESS, AI_UNAVAILABLE, QUOTA_BLOCKED, AUTH_ERROR, etc.
    error_message: Optional[str] = None

class ApplyExtractionRequest(BaseModel):
    investigation_id: int
    apply_deviation: bool = True
    apply_evidence: bool = True
    apply_five_whys: bool = False
    apply_fishbone: bool = False
    apply_root_cause: bool = False
    apply_capa: bool = False
    reviewed_fields: Optional[List[ExtractedField]] = None
    custom_overrides: Optional[Dict[str, Any]] = None
    evidence_metadata: Optional[Dict[str, Any]] = None

class ApplyRcaItemRequest(BaseModel):
    investigation_id: int
    item_type: str = Field(..., description="FIVE_WHYS, FISHBONE, ROOT_CAUSE, CAPA, EVIDENCE_GAP")
    item_data: Dict[str, Any]

class FieldPatchStatus(str, Enum):
    SOURCE_FACT = "SOURCE_FACT"
    AI_INFERENCE = "AI_INFERENCE"
    USER_CORRECTION = "USER_CORRECTION"
    MISSING = "MISSING"

class FieldPatch(BaseModel):
    field_key: str = Field(..., description="Canonical deviation field key, e.g. batch_number, equipment_id")
    label: str = Field(..., description="Human-readable label")
    value: Optional[Any] = Field(None, description="Patched value")
    status: FieldPatchStatus = Field(default=FieldPatchStatus.SOURCE_FACT)
    source_excerpt: Optional[str] = Field(None, description="Verbatim citation from source text")
    page_number: Optional[int] = Field(None, description="Page number if from multi-page document")
    reason: Optional[str] = Field(None, description="Explanation or correction rationale")
    user_attributed: Optional[str] = Field(None, description="User who executed correction if USER_CORRECTION")

class RiskAssessment(BaseModel):
    suggested_severity: str = Field(default="MAJOR", description="CRITICAL, MAJOR, MINOR")
    suggested_next_action: str = Field(..., description="Immediate containment or triage recommendation")
    initial_risk_text: str = Field(..., description="Scientific summary of batch or product safety risk")

class CopilotConverseRequest(BaseModel):
    investigation_id: int
    message: str = Field(..., max_length=100000, description="User message, pasted deviation report, or correction statement")
    attached_document_id: Optional[int] = Field(None, description="Optional ID of uploaded evidence/document")
    context_stage: Optional[str] = Field(default="INTAKE", description="Current workflow stage")
    current_draft_fields: Optional[Dict[str, Any]] = Field(default=None, description="Current client draft fields for context")

class CopilotConverseResponse(BaseModel):
    reply_text: str
    classification: str = Field(..., description="NEW_SOURCE, CORRECTION, QUESTION, ANALYSIS_REQUEST")
    field_patches: List[FieldPatch] = []
    risk_assessment: Optional[RiskAssessment] = None
    missing_fields: List[MissingInfoItem] = []
    suggested_actions: List[str] = []
    sources: Optional[List[Dict[str, Any]]] = None
    workflow_state: Optional[Dict[str, Any]] = None

class CopilotMessageRead(BaseModel):
    id: int
    investigation_id: int
    user_id: Optional[int] = None
    role: str
    content: str
    message_type: str = "TEXT"
    extra_data: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


