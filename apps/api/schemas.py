from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any
from datetime import datetime
from models import Classification


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    classification: Classification = Classification.NORMAL


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    classification: Optional[Classification] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    classification: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectEventCreate(BaseModel):
    event_type: str
    actor: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProjectEventResponse(BaseModel):
    id: int
    project_id: int
    event_type: str
    timestamp: datetime
    actor: Optional[str]
    metadata: Optional[Dict[str, Any]] = Field(alias="event_metadata")

    class Config:
        from_attributes = True
        populate_by_name = True


class DocumentResponse(BaseModel):
    id: int
    project_id: int
    filename: str
    file_type: str
    classification: str
    masked_text: str
    sanitize_level: str
    usage_restrictions: dict
    pii_gate_reasons: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    id: int
    project_id: int
    filename: str
    file_type: str
    classification: str
    sanitize_level: str
    usage_restrictions: dict
    pii_gate_reasons: Optional[dict] = None
    created_at: datetime
    # NO masked_text in list

    class Config:
        from_attributes = True

