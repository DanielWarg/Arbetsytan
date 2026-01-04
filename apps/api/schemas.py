from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from models import Classification, NoteCategory, SourceType, ProjectStatus


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    classification: Classification = Classification.NORMAL
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    classification: Optional[Classification] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class ProjectStatusUpdate(BaseModel):
    status: ProjectStatus


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    classification: str
    status: str
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
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


# Project Notes schemas
class NoteCreate(BaseModel):
    title: Optional[str] = None
    body: str  # Raw body text (will be sanitized)


class NoteResponse(BaseModel):
    id: int
    project_id: int
    title: Optional[str]
    masked_body: str  # Sanitized body
    sanitize_level: str
    pii_gate_reasons: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NoteListResponse(BaseModel):
    id: int
    project_id: int
    title: Optional[str]
    sanitize_level: str
    created_at: datetime
    # NO masked_body in list

    class Config:
        from_attributes = True


# Journalist Notes schemas (raw text, no sanitization)
class JournalistNoteCreate(BaseModel):
    title: Optional[str] = None  # Optional title/name
    body: str  # Raw body text (will be technically sanitized only)
    category: Optional[NoteCategory] = NoteCategory.RAW


class JournalistNoteUpdate(BaseModel):
    title: Optional[str] = None
    body: str  # Raw body text (will be technically sanitized only)
    category: Optional[NoteCategory] = None


class JournalistNoteResponse(BaseModel):
    id: int
    project_id: int
    title: Optional[str]
    body: str  # Raw body (no masking)
    category: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JournalistNoteListResponse(BaseModel):
    id: int
    project_id: int
    title: Optional[str]
    preview: str  # First line of body or title
    category: str
    created_at: datetime
    updated_at: datetime
    # NO body in list

    class Config:
        from_attributes = True


class JournalistNoteImageResponse(BaseModel):
    id: int
    note_id: int
    filename: str
    mime_type: str
    created_at: datetime

    class Config:
        from_attributes = True


# Project Sources schemas
class ProjectSourceCreate(BaseModel):
    title: str = Field(..., max_length=200)
    type: SourceType
    comment: Optional[str] = Field(None, max_length=500)


class ProjectSourceResponse(BaseModel):
    id: int
    project_id: int
    title: str
    type: str
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Scout schemas
class ScoutFeedCreate(BaseModel):
    name: str
    url: str


class ScoutFeedResponse(BaseModel):
    id: int
    name: str
    url: str
    is_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ScoutItemResponse(BaseModel):
    id: int
    feed_id: int
    title: str
    link: str
    published_at: Optional[datetime]
    fetched_at: datetime
    raw_source: str

    class Config:
        from_attributes = True
