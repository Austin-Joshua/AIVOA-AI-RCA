from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class DeviationBase(BaseModel):
    deviation_number: Optional[str] = Field(default=None, json_schema_extra={"example": "DEV-2026-084"})
    deviation_number_source: str = Field(default="SOURCE", json_schema_extra={"example": "SOURCE"})  # SOURCE, SYSTEM
    deviation_type: str = Field(default="MAJOR", json_schema_extra={"example": "MAJOR"})  # CRITICAL, MAJOR, MINOR
    severity: str = Field(default="High", json_schema_extra={"example": "High"})
    batch_number: str = Field(..., json_schema_extra={"example": "B2026-API-044"})
    product_name: str = Field(..., json_schema_extra={"example": "Atorvastatin Calcium Trihydrate API"})
    unit_operation: Optional[str] = Field(None, json_schema_extra={"example": "Crystallization"})
    equipment_id: Optional[str] = Field(None, json_schema_extra={"example": "RX-301"})
    bpr_number: Optional[str] = Field(None, json_schema_extra={"example": "BPR-ATV-044-REV2"})
    target_yield_kg: Optional[float] = Field(None, json_schema_extra={"example": 450.0})
    actual_yield_kg: Optional[float] = Field(None, json_schema_extra={"example": 395.2})
    occurrence_datetime: Optional[datetime] = None
    detection_datetime: Optional[datetime] = None
    description: str = Field(..., json_schema_extra={"example": "Temperature overshoot observed during critical crystallization ramp."})
    immediate_containment: Optional[str] = Field(None, json_schema_extra={"example": "Batch quarantined in mother liquor hold tank."})
    is_ai_populated: bool = False
    is_verified: bool = False

class DeviationCreate(DeviationBase):
    pass

class DeviationUpdate(BaseModel):
    deviation_number: Optional[str] = None
    deviation_number_source: Optional[str] = None
    deviation_type: Optional[str] = None
    severity: Optional[str] = None
    batch_number: Optional[str] = None
    product_name: Optional[str] = None
    unit_operation: Optional[str] = None
    equipment_id: Optional[str] = None
    bpr_number: Optional[str] = None
    target_yield_kg: Optional[float] = None
    actual_yield_kg: Optional[float] = None
    occurrence_datetime: Optional[datetime] = None
    detection_datetime: Optional[datetime] = None
    description: Optional[str] = None
    immediate_containment: Optional[str] = None
    is_ai_populated: Optional[bool] = None
    is_verified: Optional[bool] = None

class DeviationRead(DeviationBase):
    id: int
    investigation_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
