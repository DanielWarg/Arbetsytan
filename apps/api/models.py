from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


class Classification(str, enum.Enum):
    NORMAL = "normal"
    SENSITIVE = "sensitive"
    SOURCE_SENSITIVE = "source-sensitive"


class SanitizeLevel(str, enum.Enum):
    NORMAL = "normal"
    STRICT = "strict"
    PARANOID = "paranoid"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    classification = Column(SQLEnum(Classification), default=Classification.NORMAL, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    events = relationship("ProjectEvent", back_populates="project", order_by="ProjectEvent.timestamp.desc()")
    documents = relationship("Document", back_populates="project", order_by="Document.created_at.desc()")


class ProjectEvent(Base):
    __tablename__ = "project_events"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    actor = Column(String, nullable=True)
    event_metadata = Column("metadata", JSON, nullable=True)

    project = relationship("Project", back_populates="events")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # 'pdf' or 'txt'
    classification = Column(SQLEnum(Classification), nullable=False)
    masked_text = Column(Text, nullable=False)
    file_path = Column(String, nullable=False)  # Server-side only, never exposed
    sanitize_level = Column(SQLEnum(SanitizeLevel), default=SanitizeLevel.NORMAL, nullable=False)
    usage_restrictions = Column(JSON, nullable=False, default=lambda: {"ai_allowed": True, "export_allowed": True})
    pii_gate_reasons = Column(JSON, nullable=True)  # {"normal": [...], "strict": [...]}
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="documents")

