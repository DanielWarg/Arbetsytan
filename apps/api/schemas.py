from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any
from datetime import datetime
from models import Classification


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    classification: Classification = Classification.NORMAL


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

