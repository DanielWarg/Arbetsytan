from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy import or_, and_
import os
import uuid
import shutil
import logging
from typing import Optional, List
from pathlib import Path
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _safe_event_metadata(meta: dict, context: str = "audit") -> dict:
    """
    Helper function to sanitize event metadata using Privacy Guard.
    
    Args:
        meta: Raw metadata dictionary
        context: Context for sanitization ("audit" or "log")
        
    Returns:
        Sanitized metadata dictionary (forbidden keys removed/truncated)
        
    Raises:
        AssertionError: In DEV mode if forbidden keys found
    """
    sanitized = sanitize_for_logging(meta, context=context)
    assert_no_content(sanitized, context=context)
    return sanitized

from database import get_db, engine
from models import Project, ProjectEvent, Document, ProjectNote, JournalistNote, JournalistNoteImage, ProjectSource, ScoutFeed, ScoutItem, Base, Classification, SanitizeLevel, NoteCategory, SourceType, ProjectStatus
from security_core.privacy_guard import sanitize_for_logging, assert_no_content
from schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectEventCreate, ProjectEventResponse,
    DocumentResponse, DocumentListResponse, NoteCreate, NoteResponse, NoteListResponse,
    JournalistNoteCreate, JournalistNoteUpdate, JournalistNoteResponse, JournalistNoteListResponse,
    JournalistNoteImageResponse, ProjectSourceCreate, ProjectSourceResponse, ProjectStatusUpdate,
    ScoutFeedCreate, ScoutFeedResponse, ScoutItemResponse,
    FeedPreviewResponse, FeedItemPreview, CreateProjectFromFeedRequest, CreateProjectFromFeedResponse
)
from text_processing import (
    extract_text_from_pdf, extract_text_from_txt,
    normalize_text, mask_text, validate_file_type, pii_gate_check, PiiGateError,
    transcribe_audio, normalize_transcript_text, process_transcript, refine_editorial_text,
    sanitize_journalist_note
)

# Create tables
Base.metadata.create_all(bind=engine)

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Arbetsytan API")

# Preload STT engine at startup (to avoid blocking first transcription)
@app.on_event("startup")
async def preload_stt_engine():
    """Preload STT engine at startup to avoid blocking first transcription request."""
    try:
        from text_processing import _get_stt_engine
        logger.info("[STARTUP] Preloading STT engine...")
        engine, model, engine_name, model_name = _get_stt_engine()
        logger.info(f"[STARTUP] STT engine preloaded successfully: {engine_name}, model: {model_name}")
    except Exception as e:
        logger.warning(f"[STARTUP] Failed to preload STT engine: {str(e)} (will load on first use)")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic Auth
security = HTTPBasic()

# Environment variables
AUTH_MODE = os.getenv("AUTH_MODE", "basic")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
BASIC_AUTH_USER = os.getenv("BASIC_AUTH_USER", "admin")
BASIC_AUTH_PASS = os.getenv("BASIC_AUTH_PASS", "password")


def verify_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify Basic Auth credentials"""
    if AUTH_MODE != "basic":
        return True
    
    if credentials.username != BASIC_AUTH_USER or credentials.password != BASIC_AUTH_PASS:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/health")
async def health():
    """Health check endpoint (no auth required)"""
    return {
        "status": "ok",
        "demo_mode": DEMO_MODE,
        "auth_mode": AUTH_MODE
    }


@app.get("/api/hello")
async def hello(username: str = Depends(verify_basic_auth)):
    """Protected hello endpoint"""
    return {
        "message": f"Hello, {username}!",
        "demo_mode": DEMO_MODE
    }


# Projects endpoints
@app.get("/api/projects", response_model=List[ProjectResponse])
async def list_projects(
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """List all projects"""
    projects = db.query(Project).order_by(Project.updated_at.desc()).all()
    return projects


@app.post("/api/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Create a new project"""
    db_project = Project(
        name=project.name,
        description=project.description,
        classification=project.classification,
        due_date=project.due_date,
        tags=project.tags
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # Create initial event
    event = ProjectEvent(
        project_id=db_project.id,
        event_type="project_created",
        actor=username,
        event_metadata=_safe_event_metadata({"name": project.name}, context="audit")
    )
    db.add(event)
    db.commit()
    
    return db_project


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Get a specific project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.put("/api/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Update a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Track changes for event metadata
    changes = {}
    
    if project_update.name is not None:
        if project.name != project_update.name:
            changes["name"] = {"old": project.name, "new": project_update.name}
        project.name = project_update.name
    
    if project_update.description is not None:
        if project.description != project_update.description:
            changes["description"] = {"old": project.description, "new": project_update.description}
        project.description = project_update.description
    
    if project_update.classification is not None:
        if project.classification != project_update.classification:
            changes["classification"] = {"old": project.classification.value, "new": project_update.classification.value}
        project.classification = project_update.classification
    
    if project_update.due_date is not None:
        if project.due_date != project_update.due_date:
            changes["due_date"] = {"old": str(project.due_date) if project.due_date else None, "new": str(project_update.due_date) if project_update.due_date else None}
        project.due_date = project_update.due_date
    
    if project_update.tags is not None:
        if project.tags != project_update.tags:
            changes["tags"] = {"old": project.tags, "new": project_update.tags}
        project.tags = project_update.tags
    
    # Update updated_at is automatic via onupdate
    
    db.commit()
    db.refresh(project)
    
    # Create event if any changes were made
    if changes:
        event = ProjectEvent(
            project_id=project.id,
            event_type="project_updated",
            actor=username,
            event_metadata=_safe_event_metadata({"changes": changes}, context="audit")
        )
        db.add(event)
        db.commit()
    
    return project


@app.patch("/api/projects/{project_id}/status", response_model=ProjectResponse)
async def update_project_status(
    project_id: int,
    status_update: ProjectStatusUpdate,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Update project status and log event."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    old_status = project.status.value
    new_status = status_update.status.value
    
    # Update status
    project.status = status_update.status
    db.commit()
    db.refresh(project)
    
    # Log event (metadata only, via Privacy Guard)
    event_metadata = _safe_event_metadata({
        "from": old_status,
        "to": new_status
    }, context="audit")
    
    event = ProjectEvent(
        project_id=project_id,
        event_type="project_status_changed",
        actor=username,
        event_metadata=event_metadata
    )
    db.add(event)
    db.commit()
    
    logger.info(f"Project {project_id} status changed: {old_status} -> {new_status}")
    
    return project


@app.delete("/api/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """
    Delete a project and all its documents and events (permanent).
    
    Security by Design:
    - Counts files before delete
    - Deletes all files from disk
    - Verifies no orphans remain
    - Logs only metadata (no filenames/paths)
    - Fail-closed: if verification fails, log error and block delete
    """
    import os
    from pathlib import Path
    from security_core.privacy_guard import sanitize_for_logging
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # === PHASE 1: Count all files before delete ===
    files_to_delete = []
    
    # 1. Document files
    documents = db.query(Document).filter(Document.project_id == project_id).all()
    for doc in documents:
        if doc.file_path:
            file_path = UPLOAD_DIR / doc.file_path
            if file_path.exists():
                files_to_delete.append(file_path)
    
    # 2. Recording files (audio files for transcripts)
    # Note: Recordings are stored as documents with file_path, already counted above
    
    # 3. Journalist note images
    journalist_notes = db.query(JournalistNote).filter(JournalistNote.project_id == project_id).all()
    for note in journalist_notes:
        for image in note.images:
            if image.file_path:
                image_path = Path(image.file_path)
                if image_path.exists():
                    files_to_delete.append(image_path)
    
    file_count_before = len(files_to_delete)
    
    logger.info(f"[SECURE_DELETE] Project {project_id}: Found {file_count_before} files to delete")
    
    # === PHASE 2: Delete files from disk ===
    deleted_files = 0
    failed_deletes = []
    
    for file_path in files_to_delete:
        try:
            os.remove(file_path)
            deleted_files += 1
        except Exception as e:
            logger.warning(f"[SECURE_DELETE] Failed to delete file: {type(e).__name__}")
            failed_deletes.append(str(file_path))
    
    # === PHASE 3: Verify no orphans remain ===
    orphans = []
    for file_path in files_to_delete:
        if file_path.exists():
            orphans.append(str(file_path))
    
    # Fail-closed: if orphans detected, log error and block delete
    if orphans:
        logger.error(f"[SECURE_DELETE] Project {project_id}: ORPHAN DETECTION FAILED - {len(orphans)} files remain on disk")
        raise HTTPException(
            status_code=500,
            detail=f"Secure delete failed: {len(orphans)} orphan files detected. Delete blocked for security."
        )
    
    # === PHASE 4: Delete DB records (CASCADE) ===
    # Delete events first (explicit cascade)
    db.query(ProjectEvent).filter(ProjectEvent.project_id == project_id).delete()
    # Delete documents (cascade should handle, but explicit for safety)
    db.query(Document).filter(Document.project_id == project_id).delete()
    # Delete project notes (cascade will delete journalist notes and images)
    db.query(ProjectNote).filter(ProjectNote.project_id == project_id).delete()
    db.query(JournalistNote).filter(JournalistNote.project_id == project_id).delete()
    # Delete project
    db.delete(project)
    db.commit()
    
    # === PHASE 5: Log only metadata (privacy-safe) ===
    safe_metadata = sanitize_for_logging({
        "project_id": project_id,
        "files_counted": file_count_before,
        "files_deleted": deleted_files,
        "files_failed": len(failed_deletes),
        "orphans_detected": len(orphans),
        "actor": username
    }, context="audit")
    
    logger.info(f"[SECURE_DELETE] Project {project_id} deleted successfully", extra=safe_metadata)
    
    return None


@app.get("/api/projects/{project_id}/events", response_model=List[ProjectEventResponse])
async def get_project_events(
    project_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Get events for a specific project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    events = db.query(ProjectEvent).filter(
        ProjectEvent.project_id == project_id
    ).order_by(ProjectEvent.timestamp.desc()).all()
    return events


@app.post("/api/projects/{project_id}/events", response_model=ProjectEventResponse, status_code=201)
async def create_project_event(
    project_id: int,
    event: ProjectEventCreate,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Create an event for a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db_event = ProjectEvent(
        project_id=project_id,
        event_type=event.event_type,
        actor=event.actor or username,
        event_metadata=_safe_event_metadata(event.metadata or {}, context="audit")
    )
    db.add(db_event)
    
    # Update project updated_at
    from sqlalchemy.sql import func
    project.updated_at = func.now()
    
    db.commit()
    db.refresh(db_event)
    return db_event


# Documents endpoints
@app.post("/api/projects/{project_id}/documents", response_model=DocumentListResponse, status_code=201)
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """
    Upload a document to a project.
    Returns metadata only (no masked_text).
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate file size (25MB max)
    file_content = await file.read()
    if len(file_content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 25MB")
    
    # Save file temporarily for validation and processing
    temp_path = UPLOAD_DIR / f"temp_{uuid.uuid4()}"
    try:
        with open(temp_path, 'wb') as f:
            f.write(file_content)
        
        # Validate file type (extension + magic bytes)
        file_type, is_valid = validate_file_type(str(temp_path), file.filename)
        if not is_valid:
            os.remove(temp_path)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Only PDF and TXT files are allowed. PDF must start with %PDF-, TXT must be valid text."
            )
        
        # Extract text
        try:
            if file_type == 'pdf':
                raw_text = extract_text_from_pdf(str(temp_path))
            else:  # txt
                raw_text = extract_text_from_txt(str(temp_path))
        except Exception as e:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")
        
        # Normalize text
        normalized_text = normalize_text(raw_text)
        
        # Progressive sanitization pipeline
        pii_gate_reasons = {}
        sanitize_level = SanitizeLevel.NORMAL
        usage_restrictions = {"ai_allowed": True, "export_allowed": True}
        masked_text = None
        
        # Try normal masking
        masked_text = mask_text(normalized_text, level="normal")
        is_safe, reasons = pii_gate_check(masked_text)
        if is_safe:
            sanitize_level = SanitizeLevel.NORMAL
            pii_gate_reasons = None
        else:
            pii_gate_reasons["normal"] = reasons
            
            # Try strict masking
            masked_text = mask_text(normalized_text, level="strict")
            is_safe, reasons = pii_gate_check(masked_text)
            if is_safe:
                sanitize_level = SanitizeLevel.STRICT
                usage_restrictions = {"ai_allowed": True, "export_allowed": True}
            else:
                pii_gate_reasons["strict"] = reasons
                
                # Use paranoid masking (must always pass gate)
                masked_text = mask_text(normalized_text, level="paranoid")
                is_safe, reasons = pii_gate_check(masked_text)
                
                if not is_safe:
                    # This should never happen - paranoid must guarantee gate pass
                    os.remove(temp_path)
                    raise HTTPException(
                        status_code=500,
                        detail="Internal error: Paranoid masking failed PII gate check. This is a bug."
                    )
                
                sanitize_level = SanitizeLevel.PARANOID
                usage_restrictions = {"ai_allowed": False, "export_allowed": False}
        
        # Move file to permanent location
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1]
        permanent_path = UPLOAD_DIR / f"{file_id}{file_ext}"
        shutil.move(str(temp_path), str(permanent_path))
        
        # Create document record
        db_document = Document(
            project_id=project_id,
            filename=file.filename,
            file_type=file_type,
            classification=project.classification,  # Inherit from project
            masked_text=masked_text,
            file_path=str(permanent_path),  # Never exposed via API
            sanitize_level=sanitize_level,
            usage_restrictions=usage_restrictions,
            pii_gate_reasons=pii_gate_reasons if pii_gate_reasons else None
        )
        db.add(db_document)
        
        # Update project updated_at
        from sqlalchemy.sql import func
        project.updated_at = func.now()
        
        # Create event
        event = ProjectEvent(
            project_id=project_id,
            event_type="document_uploaded",
            actor=username,
            event_metadata=_safe_event_metadata({"file_type": file_type}, context="audit")
        )
        db.add(event)
        
        db.commit()
        db.refresh(db_document)
        
        # Return metadata only (no masked_text)
        return DocumentListResponse(
            id=db_document.id,
            project_id=db_document.project_id,
            filename=db_document.filename,
            file_type=db_document.file_type,
            classification=db_document.classification.value,
            sanitize_level=db_document.sanitize_level.value,
            usage_restrictions=db_document.usage_restrictions,
            pii_gate_reasons=db_document.pii_gate_reasons,
            created_at=db_document.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Cleanup on error
        if temp_path.exists():
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/projects/{project_id}/documents", response_model=List[DocumentListResponse])
async def list_documents(
    project_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """
    List all documents for a project.
    Returns metadata only (no masked_text, no file_path).
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    documents = db.query(Document).filter(
        Document.project_id == project_id
    ).order_by(Document.created_at.desc()).all()
    
    return [
        DocumentListResponse(
            id=doc.id,
            project_id=doc.project_id,
            filename=doc.filename,
            file_type=doc.file_type,
            classification=doc.classification.value,
            sanitize_level=doc.sanitize_level.value,
            usage_restrictions=doc.usage_restrictions,
            pii_gate_reasons=doc.pii_gate_reasons,
            created_at=doc.created_at
        )
        for doc in documents
    ]


@app.get("/api/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """
    Get a specific document.
    Returns masked_text + metadata only (no file_path).
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=document.id,
        project_id=document.project_id,
        filename=document.filename,
        file_type=document.file_type,
        classification=document.classification.value,
        masked_text=document.masked_text,
        sanitize_level=document.sanitize_level.value,
        usage_restrictions=document.usage_restrictions,
        pii_gate_reasons=document.pii_gate_reasons,
        created_at=document.created_at
    )


@app.delete("/api/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """
    Delete a document and its associated files.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete associated files if they exist
    import os
    if document.file_path and os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except Exception as e:
            logger.error(f"Failed to delete file {document.file_path}: {e}")
    
    # Delete audio file if it exists (for recordings)
    if hasattr(document, 'audio_path') and document.audio_path and os.path.exists(document.audio_path):
        try:
            os.remove(document.audio_path)
        except Exception as e:
            logger.error(f"Failed to delete audio file {document.audio_path}: {e}")
    
    # Delete from database
    db.delete(document)
    db.commit()
    
    # Log event
    log_event(
        db=db,
        project_id=document.project_id,
        event_type="document_deleted",
        actor=username,
        metadata={
            "document_id": document_id,
            "filename": document.filename
        }
    )
    
    return Response(status_code=204)


# Recordings endpoint
@app.post("/api/projects/{project_id}/recordings", response_model=DocumentListResponse, status_code=201)
async def upload_recording(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """
    Upload an audio recording and process it into a transcript document.
    Returns metadata only (no masked_text, no raw transcript).
    
    NEVER logs raw transcript or raw document content.
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate file size (25MB max)
    file_content = await file.read()
    file_size = len(file_content)
    if file_size > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 25MB")
    
    # TEMP LOG: Audio file received (metadata only)
    logger.info(f"[AUDIO] Audio file received: filename={file.filename}, size={file_size} bytes, mime={file.content_type}")
    
    # Save audio file to permanent location (never exposed via API)
    audio_file_id = str(uuid.uuid4())
    audio_ext = os.path.splitext(file.filename)[1] or '.mp3'
    audio_path = UPLOAD_DIR / f"{audio_file_id}{audio_ext}"
    
    try:
        with open(audio_path, 'wb') as f:
            f.write(file_content)
        logger.info(f"[AUDIO] Audio file saved: {audio_path}")
    except Exception as e:
        logger.error(f"[AUDIO] Failed to save audio file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save audio file: {str(e)}")
    
    # Get file metadata (mime type, size)
    # Use actual content-type if available, fallback to application/octet-stream
    mime_type = file.content_type or "application/octet-stream"
    
    # Transcribe audio using local STT (openai-whisper)
    # NEVER log raw transcript
    logger.info(f"[AUDIO] Starting transcription...")
    try:
        raw_transcript = transcribe_audio(str(audio_path))
        transcript_length = len(raw_transcript) if raw_transcript else 0
        logger.info(f"[AUDIO] Transcription finished: transcript_length={transcript_length} chars")
    except Exception as e:
        logger.error(f"[AUDIO] Transcription failed: {str(e)}")
        # Fail-closed: cleanup and raise error (no document created)
        if audio_path.exists():
            os.remove(audio_path)
        raise HTTPException(
            status_code=400,
            detail=f"Audio transcription failed: {str(e)}"
        )
    
    # Normalize transcript text (deterministic post-processing)
    normalized_transcript = normalize_transcript_text(raw_transcript)
    normalized_length = len(normalized_transcript) if normalized_transcript else 0
    logger.info(f"[AUDIO] Transcript normalized: length={normalized_length} chars (was {transcript_length})")
    
    # Get actual duration from transcription (if available)
    # For now, estimate from file size (can be improved with audio metadata)
    estimated_duration = None
    if file_size > 0:
        # Rough estimate: assume ~128kbps = ~1MB per minute
        estimated_duration = int((file_size / (1024 * 1024)) * 60)
    
    # Process transcript into structured format
    recording_date = datetime.now().strftime("%Y-%m-%d")
    processed_text = process_transcript(normalized_transcript, project.name, recording_date, estimated_duration)
    
    # Refine to editorial-ready first draft (deterministic)
    processed_text = refine_editorial_text(processed_text)
    
    # Create temporary TXT file with processed text
    temp_txt_path = UPLOAD_DIR / f"temp_transcript_{uuid.uuid4()}.txt"
    try:
        with open(temp_txt_path, 'w', encoding='utf-8') as f:
            f.write(processed_text)
    except Exception as e:
        # Cleanup audio file
        if audio_path.exists():
            os.remove(audio_path)
        raise HTTPException(status_code=500, detail=f"Failed to create transcript file: {str(e)}")
    
    # Feed processed text into existing ingest pipeline (same as TXT upload)
    try:
        # Normalize text
        normalized_text = normalize_text(processed_text)
        
        # Progressive sanitization pipeline (same as document upload)
        pii_gate_reasons = {}
        sanitize_level = SanitizeLevel.NORMAL
        usage_restrictions = {"ai_allowed": True, "export_allowed": True}
        masked_text = None
        
        # Try normal masking
        masked_text = mask_text(normalized_text, level="normal")
        is_safe, reasons = pii_gate_check(masked_text)
        if is_safe:
            sanitize_level = SanitizeLevel.NORMAL
            pii_gate_reasons = None
        else:
            pii_gate_reasons["normal"] = reasons
            
            # Try strict masking
            masked_text = mask_text(normalized_text, level="strict")
            is_safe, reasons = pii_gate_check(masked_text)
            if is_safe:
                sanitize_level = SanitizeLevel.STRICT
                usage_restrictions = {"ai_allowed": True, "export_allowed": True}
            else:
                pii_gate_reasons["strict"] = reasons
                
                # Use paranoid masking (must always pass gate)
                masked_text = mask_text(normalized_text, level="paranoid")
                is_safe, reasons = pii_gate_check(masked_text)
                
                if not is_safe:
                    # This should never happen - paranoid must guarantee gate pass
                    os.remove(temp_txt_path)
                    if audio_path.exists():
                        os.remove(audio_path)
                    raise HTTPException(
                        status_code=500,
                        detail="Internal error: Paranoid masking failed PII gate check. This is a bug."
                    )
                
                sanitize_level = SanitizeLevel.PARANOID
                usage_restrictions = {"ai_allowed": False, "export_allowed": False}
        
        # Move TXT file to permanent location
        txt_file_id = str(uuid.uuid4())
        permanent_txt_path = UPLOAD_DIR / f"{txt_file_id}.txt"
        shutil.move(str(temp_txt_path), str(permanent_txt_path))
        
        # Create document record (filename: rostmemo-{timestamp}.txt)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        document_filename = f"röstmemo-{timestamp}.txt"
        
        db_document = Document(
            project_id=project_id,
            filename=document_filename,
            file_type='txt',
            classification=project.classification,  # Inherit from project
            masked_text=masked_text,
            file_path=str(permanent_txt_path),  # Never exposed via API
            sanitize_level=sanitize_level,
            usage_restrictions=usage_restrictions,
            pii_gate_reasons=pii_gate_reasons if pii_gate_reasons else None
        )
        db.add(db_document)
        
        # Update project updated_at
        from sqlalchemy.sql import func
        project.updated_at = func.now()
        
        # Create event: recording_transcribed with ONLY metadata (no raw transcript)
        event_metadata = {
            "size": file_size,
            "mime": mime_type,
        }
        if estimated_duration:
            event_metadata["duration_seconds"] = estimated_duration
        # Store reference to audio file (non-exposed)
        event_metadata["recording_file_id"] = audio_file_id
        
        event = ProjectEvent(
            project_id=project_id,
            event_type="recording_transcribed",
            actor=username,
            event_metadata=_safe_event_metadata(event_metadata, context="audit")
        )
        db.add(event)
        
        logger.info(f"[AUDIO] Creating document...")
        db.commit()
        db.refresh(db_document)
        logger.info(f"[AUDIO] Document created with id={db_document.id}")
        
        # Return metadata only (no masked_text, no raw transcript)
        return DocumentListResponse(
            id=db_document.id,
            project_id=db_document.project_id,
            filename=db_document.filename,
            file_type=db_document.file_type,
            classification=db_document.classification.value,
            sanitize_level=db_document.sanitize_level.value,
            usage_restrictions=db_document.usage_restrictions,
            pii_gate_reasons=db_document.pii_gate_reasons,
            created_at=db_document.created_at
        )
        
    except HTTPException:
        # Cleanup on error
        if temp_txt_path.exists():
            os.remove(temp_txt_path)
        if audio_path.exists():
            os.remove(audio_path)
        raise
    except Exception as e:
        # Cleanup on error
        if temp_txt_path.exists():
            os.remove(temp_txt_path)
        if audio_path.exists():
            os.remove(audio_path)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# ============================================================================
# Project Notes endpoints
# ============================================================================

@app.get("/api/projects/{project_id}/notes", response_model=List[NoteListResponse])
async def list_project_notes(
    project_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """List all notes for a project (metadata only, no masked_body)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    notes = db.query(ProjectNote).filter(ProjectNote.project_id == project_id).order_by(ProjectNote.created_at.desc()).all()
    return notes


@app.post("/api/projects/{project_id}/notes", response_model=NoteResponse, status_code=201)
async def create_note(
    project_id: int,
    note: NoteCreate,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """
    Create a note for a project.
    Body goes through same normalize/mask/sanitization pipeline as documents.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Normalize text
    normalized_text = normalize_text(note.body)
    
    # Progressive sanitization pipeline (same as documents)
    pii_gate_reasons = {}
    sanitize_level = SanitizeLevel.NORMAL
    usage_restrictions = {"ai_allowed": True, "export_allowed": True}
    
    # Try normal masking
    masked_text = mask_text(normalized_text, level="normal")
    is_safe, reasons = pii_gate_check(masked_text)
    if is_safe:
        sanitize_level = SanitizeLevel.NORMAL
        pii_gate_reasons = None
    else:
        pii_gate_reasons["normal"] = reasons
        
        # Try strict masking
        masked_text = mask_text(normalized_text, level="strict")
        is_safe, reasons = pii_gate_check(masked_text)
        if is_safe:
            sanitize_level = SanitizeLevel.STRICT
        else:
            pii_gate_reasons["strict"] = reasons
            
            # Use paranoid masking
            masked_text = mask_text(normalized_text, level="paranoid")
            sanitize_level = SanitizeLevel.PARANOID
            usage_restrictions = {"ai_allowed": False, "export_allowed": False}
    
    # Create note
    db_note = ProjectNote(
        project_id=project_id,
        title=note.title,
        masked_body=masked_text,
        sanitize_level=sanitize_level,
        pii_gate_reasons=pii_gate_reasons if pii_gate_reasons else None
    )
    db.add(db_note)
    
    # Create event (metadata only)
    event = ProjectEvent(
        project_id=project_id,
        event_type="note_created",
        actor=username,
        event_metadata=_safe_event_metadata({
            "note_id": None,  # Will be set after commit
            "sanitize_level": sanitize_level.value
        }, context="audit")
    )
    db.add(event)
    
    db.commit()
    db.refresh(db_note)
    
    # Update event with note_id
    event.event_metadata["note_id"] = db_note.id
    db.commit()
    
    return db_note


@app.get("/api/notes/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Get a specific note with masked body."""
    note = db.query(ProjectNote).filter(ProjectNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.delete("/api/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Delete a note."""
    note = db.query(ProjectNote).filter(ProjectNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    project_id = note.project_id
    db.delete(note)
    
    # Create deletion event
    event = ProjectEvent(
        project_id=project_id,
        event_type="note_deleted",
        actor=username,
        event_metadata=_safe_event_metadata({"note_id": note_id}, context="audit")
    )
    db.add(event)
    
    db.commit()
    return None


# Journalist Notes endpoints
# ============================================================================

@app.get("/api/projects/{project_id}/journalist-notes", response_model=List[JournalistNoteListResponse])
async def list_journalist_notes(
    project_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """List all journalist notes for a project (metadata only, no body)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    notes = db.query(JournalistNote).filter(JournalistNote.project_id == project_id).order_by(JournalistNote.updated_at.desc()).all()
    
    # Build list response with preview (title or first line of body)
    result = []
    for note in notes:
        # Use title if available, otherwise first line of body
        if note.title:
            preview = note.title
        else:
            preview = note.body.split('\n')[0] if note.body else ""
            if len(preview) > 100:
                preview = preview[:100] + "..."
        
        result.append(JournalistNoteListResponse(
            id=note.id,
            project_id=note.project_id,
            title=note.title,
            preview=preview,
            category=note.category.value,
            created_at=note.created_at,
            updated_at=note.updated_at
        ))
    
    return result


@app.get("/api/journalist-notes/{note_id}", response_model=JournalistNoteResponse)
async def get_journalist_note(
    note_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Get a specific journalist note with raw body."""
    note = db.query(JournalistNote).filter(JournalistNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.get("/api/journalist-notes/{note_id}/images", response_model=List[JournalistNoteImageResponse])
async def list_journalist_note_images(
    note_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """List all images for a journalist note."""
    note = db.query(JournalistNote).filter(JournalistNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    images = db.query(JournalistNoteImage).filter(JournalistNoteImage.note_id == note_id).order_by(JournalistNoteImage.created_at.desc()).all()
    return images


@app.post("/api/projects/{project_id}/journalist-notes", response_model=JournalistNoteResponse, status_code=201)
async def create_journalist_note(
    project_id: int,
    note: JournalistNoteCreate,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """
    Create a journalist note.
    Only technical sanitization (no masking, no normalization, no AI).
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Technical sanitization only (no masking, no normalization)
    sanitized_body = sanitize_journalist_note(note.body)
    
    # Sanitize title if provided
    sanitized_title = None
    if note.title:
        sanitized_title = sanitize_journalist_note(note.title).strip()
        if not sanitized_title:
            sanitized_title = None
    
    # Create note
    db_note = JournalistNote(
        project_id=project_id,
        title=sanitized_title,
        body=sanitized_body,
        category=note.category or NoteCategory.RAW
    )
    db.add(db_note)
    
    # Create event (metadata only - NEVER content)
    event = ProjectEvent(
        project_id=project_id,
        event_type="note_created",
        actor=username,
        event_metadata=_safe_event_metadata({
            "note_id": None,  # Will be set after commit
            "note_type": "journalist"
        }, context="audit")
    )
    db.add(event)
    
    db.commit()
    db.refresh(db_note)
    
    # Update event with note_id
    event.event_metadata["note_id"] = db_note.id
    db.commit()
    
    return db_note


@app.put("/api/journalist-notes/{note_id}", response_model=JournalistNoteResponse)
async def update_journalist_note(
    note_id: int,
    note: JournalistNoteUpdate,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """
    Update a journalist note.
    Only technical sanitization (no masking, no normalization, no AI).
    """
    db_note = db.query(JournalistNote).filter(JournalistNote.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Technical sanitization only
    sanitized_body = sanitize_journalist_note(note.body)
    
    # Sanitize title if provided
    if note.title is not None:
        sanitized_title = sanitize_journalist_note(note.title).strip()
        db_note.title = sanitized_title if sanitized_title else None
    # If title is not provided in update, keep existing title
    
    db_note.body = sanitized_body
    
    # Update category if provided
    if note.category is not None:
        db_note.category = note.category
    
    # updated_at is set automatically by onupdate
    
    # Create event (metadata only)
    event = ProjectEvent(
        project_id=db_note.project_id,
        event_type="note_updated",
        actor=username,
        event_metadata=_safe_event_metadata({
            "note_id": note_id,
            "note_type": "journalist"
        }, context="audit")
    )
    db.add(event)
    
    # Update project updated_at
    from sqlalchemy.sql import func
    project = db.query(Project).filter(Project.id == db_note.project_id).first()
    if project:
        project.updated_at = func.now()
    
    db.commit()
    db.refresh(db_note)
    
    return db_note


@app.delete("/api/journalist-notes/{note_id}", status_code=204)
async def delete_journalist_note(
    note_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Delete a journalist note and associated images."""
    note = db.query(JournalistNote).filter(JournalistNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    project_id = note.project_id
    
    # Delete associated images from disk
    images = db.query(JournalistNoteImage).filter(JournalistNoteImage.note_id == note_id).all()
    for image in images:
        image_path = UPLOAD_DIR / image.file_path
        if image_path.exists():
            try:
                os.remove(image_path)
            except Exception:
                pass  # Ignore errors
    
    # Delete note (cascade will delete images from DB)
    db.delete(note)
    
    # Create deletion event
    event = ProjectEvent(
        project_id=project_id,
        event_type="note_deleted",
        actor=username,
        event_metadata=_safe_event_metadata({
            "note_id": note_id,
            "note_type": "journalist"
        }, context="audit")
    )
    db.add(event)
    
    db.commit()
    return None


@app.get("/api/projects/{project_id}/export")
async def export_project_markdown(
    project_id: int,
    include_metadata: bool = Query(True),
    include_transcripts: bool = Query(False),
    include_notes: bool = Query(False),
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Export project as Markdown. Notes OFF by default for privacy."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Fetch data
    documents = db.query(Document).filter(Document.project_id == project_id).order_by(Document.created_at).all()
    transcripts = db.query(ProjectNote).filter(ProjectNote.project_id == project_id).order_by(ProjectNote.created_at).all()
    sources = db.query(ProjectSource).filter(ProjectSource.project_id == project_id).order_by(ProjectSource.created_at).all()
    journalist_notes = db.query(JournalistNote).filter(JournalistNote.project_id == project_id).order_by(JournalistNote.created_at).all()
    
    # Build Markdown (follow template exactly)
    md = f"# Projekt: {project.name}\n\n"
    
    # Project metadata (only if include_metadata=true)
    if include_metadata:
        md += f"Projekt-ID: {project.id}\n"
        md += f"Status: {project.status.value}\n"
        md += f"Skapad: {project.created_at.strftime('%Y-%m-%d')}\n"
        md += f"Uppdaterad: {project.updated_at.strftime('%Y-%m-%d')}\n\n"
    else:
        md += "\n"
    
    # Export settings
    md += "## Exportinställningar\n\n"
    md += f"Inkludera metadata: {include_metadata}\n"
    md += f"Inkludera röstmemo/transkript: {include_transcripts}\n"
    md += f"Inkludera anteckningar: {include_notes}\n"
    if include_metadata:
        md += f"Skapad av: {username}\n"
    md += f"Exportdatum: {datetime.now().strftime('%Y-%m-%d')}\n\n"
    
    # Sources (only if include_metadata=true)
    md += "## Källor\n\n"
    if include_metadata:
        md += "(Detta är metadata som journalisten manuellt har lagt till.)\n\n"
        if sources:
            for src in sources:
                type_label = {"link": "Länk", "person": "Person", "document": "Dokument", "other": "Övrigt"}.get(src.type.value, src.type.value)
                md += f"**{type_label}** — {src.title}\n"
                if src.comment:
                    md += f"Kommentar: {src.comment}\n"
                md += f"Skapad: {src.created_at.strftime('%Y-%m-%d')}\n\n"
        else:
            md += "*(Inget att visa)*\n\n"
    else:
        md += "*(Ej inkluderat i denna export)*\n\n"
    
    # Documents (always included)
    md += "## Dokument\n\n"
    if documents:
        for doc in documents:
            md += f"### {doc.filename}\n\n"
            if include_metadata:
                md += f"Dokument-ID: {doc.id}\n"
            md += f"Skapad: {doc.created_at.strftime('%Y-%m-%d')}\n\n"
            md += f"{doc.masked_text}\n\n"
    else:
        md += "*(Inget att visa)*\n\n"
    
    # Transcripts (only if toggled)
    md += "## Röstmemo / Transkript\n\n"
    if include_transcripts:
        if transcripts:
            for trans in transcripts:
                title = trans.title if trans.title else "Namnlöst transkript"
                md += f"### {title}\n\n"
                if include_metadata:
                    md += f"Transkript-ID: {trans.id}\n"
                md += f"Skapad: {trans.created_at.strftime('%Y-%m-%d')}\n\n"
                md += f"{trans.masked_body}\n\n"
        else:
            md += "*(Inget att visa)*\n\n"
    else:
        md += "*(Ej inkluderat i denna export)*\n\n"
    
    # Notes (only if explicitly toggled, OFF by default)
    md += "## Anteckningar\n\n"
    if include_notes:
        if journalist_notes:
            for note in journalist_notes:
                title = note.title if note.title else "Namnlös anteckning"
                md += f"### {title}\n\n"
                if include_metadata:
                    md += f"Antecknings-ID: {note.id}\n"
                    md += f"Kategori: {note.category.value}\n"
                md += f"Skapad: {note.created_at.strftime('%Y-%m-%d')}\n"
                md += f"Uppdaterad: {note.updated_at.strftime('%Y-%m-%d')}\n\n"
                md += f"{note.body}\n\n"
        else:
            md += "*(Inget att visa)*\n\n"
    else:
        md += "*(Ej inkluderat i denna export)*\n\n"
    
    # Footer
    md += "---\n\n"
    md += "## Integritetsnotis\n\n"
    md += "Denna export kan innehålla sanerat material från dokument och (om valt) transkript.\n"
    md += "Privata anteckningar inkluderas inte som standard.\n"
    md += "Systemets events/loggar innehåller aldrig innehåll, endast metadata.\n"
    
    # Log event (metadata only, NO CONTENT)
    event_metadata = _safe_event_metadata({
        "format": "markdown",
        "include_metadata": include_metadata,
        "include_transcripts": include_transcripts,
        "include_notes": include_notes
    }, context="audit")
    
    event = ProjectEvent(
        project_id=project_id,
        event_type="export_created",
        actor=username,
        event_metadata=event_metadata
    )
    db.add(event)
    db.commit()
    
    logger.info(f"Project {project_id} exported (format=markdown, notes={include_notes}, transcripts={include_transcripts})")
    
    # Return as downloadable file
    filename = f"project_{project_id}_export.md"
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.post("/api/journalist-notes/{note_id}/images", response_model=JournalistNoteImageResponse, status_code=201)
async def upload_journalist_note_image(
    note_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """
    Upload an image to a journalist note.
    Images are private references only - no analysis, no OCR, no AI.
    """
    note = db.query(JournalistNote).filter(JournalistNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Validate file size (10MB max)
    file_content = await file.read()
    file_size = len(file_content)
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large. Maximum size is 10MB")
    
    # Validate image format
    mime_type = file.content_type or ""
    if not mime_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Create directory for note images
    note_images_dir = UPLOAD_DIR / "journalist_notes" / str(note_id)
    note_images_dir.mkdir(parents=True, exist_ok=True)
    
    # Save image
    image_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1] or '.jpg'
    image_path = note_images_dir / f"{image_id}{file_ext}"
    
    try:
        with open(image_path, 'wb') as f:
            f.write(file_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")
    
    # Create image record
    db_image = JournalistNoteImage(
        note_id=note_id,
        file_path=f"journalist_notes/{note_id}/{image_id}{file_ext}",  # Relative path
        filename=file.filename,
        mime_type=mime_type
    )
    db.add(db_image)
    
    # Create event (metadata only - NEVER image content)
    event = ProjectEvent(
        project_id=note.project_id,
        event_type="note_image_added",
        actor=username,
        event_metadata=_safe_event_metadata({
            "note_id": note_id,
            "image_id": None,  # Will be set after commit
            "mime_type": mime_type,
            "size": file_size
        }, context="audit")
    )
    db.add(event)
    
    db.commit()
    db.refresh(db_image)
    
    # Update event with image_id
    event.event_metadata["image_id"] = db_image.id
    db.commit()
    
    return db_image


@app.get("/api/journalist-notes/{note_id}/images/{image_id}")
async def get_journalist_note_image(
    note_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Get an image file for inline display."""
    note = db.query(JournalistNote).filter(JournalistNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    image = db.query(JournalistNoteImage).filter(
        JournalistNoteImage.id == image_id,
        JournalistNoteImage.note_id == note_id
    ).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    image_path = UPLOAD_DIR / image.file_path
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    
    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(image_path),
        media_type=image.mime_type,
        filename=image.filename
    )


# ===== PROJECT SOURCES ENDPOINTS =====

@app.post("/api/projects/{project_id}/sources", response_model=ProjectSourceResponse, status_code=201)
async def create_project_source(
    project_id: int,
    source_data: ProjectSourceCreate,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Create a new source/reference for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create source
    source = ProjectSource(
        project_id=project_id,
        title=source_data.title,
        type=source_data.type,
        comment=source_data.comment
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    
    # Log event (metadata only: type + timestamp, NO title/comment)
    event_metadata = _safe_event_metadata({
        "type": source_data.type.value
    }, context="audit")
    
    event = ProjectEvent(
        project_id=project_id,
        event_type="source_added",
        actor=username,
        event_metadata=event_metadata
    )
    db.add(event)
    db.commit()
    
    logger.info(f"Source added to project {project_id}: type={source_data.type.value}")
    
    return source


@app.get("/api/projects/{project_id}/sources", response_model=List[ProjectSourceResponse])
async def get_project_sources(
    project_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Get all sources for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    sources = db.query(ProjectSource).filter(ProjectSource.project_id == project_id).order_by(ProjectSource.created_at.desc()).all()
    return sources


@app.delete("/api/projects/{project_id}/sources/{source_id}", status_code=204)
async def delete_project_source(
    project_id: int,
    source_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Delete a source (hard delete)."""
    source = db.query(ProjectSource).filter(
        ProjectSource.id == source_id,
        ProjectSource.project_id == project_id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    source_type = source.type.value
    
    # Delete source
    db.delete(source)
    db.commit()
    
    # Log event (metadata only: type, NO title/comment)
    event_metadata = _safe_event_metadata({
        "type": source_type
    }, context="audit")
    
    event = ProjectEvent(
        project_id=project_id,
        event_type="source_removed",
        actor=username,
        event_metadata=event_metadata
    )
    db.add(event)
    db.commit()
    
    logger.info(f"Source removed from project {project_id}: type={source_type}")
    
    return None


# Scout endpoints
@app.get("/api/scout/feeds", response_model=List[ScoutFeedResponse])
async def list_scout_feeds(
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """List all Scout feeds. Lazy seed: creates default feeds if table is empty."""
    # Lazy seed: if no feeds exist, create defaults
    feed_count = db.query(ScoutFeed).count()
    if feed_count == 0:
        defaults = [
            ScoutFeed(
                name="Polisen – Händelser Västra Götaland",
                url="https://polisen.se/aktuellt/rss/vastra-gotaland/handelser-rss---vastra-gotaland/",
                is_enabled=True
            ),
            ScoutFeed(
                name="Polisen – Pressmeddelanden Västra Götaland",
                url="https://polisen.se/aktuellt/rss/vastra-gotaland/pressmeddelanden-rss---vastra-gotaland/",
                is_enabled=True
            ),
            ScoutFeed(
                name="Göteborgs tingsrätt",
                url="https://www.domstol.se/feed/56/?searchPageId=1139&scope=news",
                is_enabled=True
            )
        ]
        for feed in defaults:
            db.add(feed)
        db.commit()
        logger.info("Scout: Created 3 default feeds (all enabled)")
    else:
        # Kontrollera om Göteborgs tingsrätt feed saknas och lägg till den
        domstol_feed = db.query(ScoutFeed).filter(
            ScoutFeed.url == "https://www.domstol.se/feed/56/?searchPageId=1139&scope=news"
        ).first()
        if not domstol_feed:
            new_feed = ScoutFeed(
                name="Göteborgs tingsrätt",
                url="https://www.domstol.se/feed/56/?searchPageId=1139&scope=news",
                is_enabled=True
            )
            db.add(new_feed)
            db.commit()
            logger.info("Scout: Added Göteborgs tingsrätt feed to existing feeds")
    
    feeds = db.query(ScoutFeed).all()
    return feeds


@app.post("/api/scout/feeds", response_model=ScoutFeedResponse, status_code=201)
async def create_scout_feed(
    feed_data: ScoutFeedCreate,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Create a new Scout feed."""
    feed = ScoutFeed(
        name=feed_data.name,
        url=feed_data.url,
        is_enabled=True
    )
    db.add(feed)
    db.commit()
    db.refresh(feed)
    return feed


@app.delete("/api/scout/feeds/{feed_id}", status_code=204)
async def delete_scout_feed(
    feed_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Disable a Scout feed (soft delete)."""
    feed = db.query(ScoutFeed).filter(ScoutFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    
    feed.is_enabled = False
    db.commit()
    return None


@app.get("/api/scout/items", response_model=List[ScoutItemResponse])
async def list_scout_items(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """List Scout items from last N hours."""
    from datetime import timedelta
    from sqlalchemy import func as sql_func
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Filter: (published_at >= cutoff) OR (published_at IS NULL AND fetched_at >= cutoff)
    items = db.query(ScoutItem).filter(
        or_(
            ScoutItem.published_at >= cutoff,
            and_(ScoutItem.published_at.is_(None), ScoutItem.fetched_at >= cutoff)
        )
    ).order_by(
        sql_func.coalesce(ScoutItem.published_at, ScoutItem.fetched_at).desc()
    ).limit(limit).all()
    
    return items


@app.post("/api/scout/fetch")
async def fetch_scout_feeds(
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Manually trigger RSS feed fetch."""
    from scout import fetch_all_feeds
    
    results = fetch_all_feeds(db)
    return {"feeds_processed": len(results), "results": results}


# ===== FEED IMPORT ENDPOINTS =====

@app.get("/api/feeds/preview", response_model=FeedPreviewResponse)
async def preview_feed(
    url: str = Query(..., description="Feed URL to preview"),
    username: str = Depends(verify_basic_auth)
):
    """
    Preview a feed without creating a project.
    Returns feed metadata and items (no storage).
    """
    from feeds import validate_and_fetch, parse_feed
    
    try:
        # Fetch and validate URL (SSRF protection)
        content = validate_and_fetch(url)
        
        # Parse feed
        feed_data = parse_feed(content)
        
        # Convert to response format
        items = [
            FeedItemPreview(
                guid=item['guid'],
                title=item['title'],
                link=item['link'],
                published=item['published'],
                summary_text=item['summary_text']
            )
            for item in feed_data['items']
        ]
        
        return FeedPreviewResponse(
            title=feed_data['title'],
            description=feed_data['description'],
            items=items
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Feed preview failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to preview feed: {str(e)}")


@app.post("/api/projects/from-feed", response_model=CreateProjectFromFeedResponse, status_code=201)
async def create_project_from_feed(
    request: CreateProjectFromFeedRequest,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """
    Create a project from a feed URL.
    Imports feed items as documents using the same ingest pipeline as regular documents.
    """
    from feeds import validate_and_fetch, parse_feed
    
    try:
        # Fetch and parse feed
        content = validate_and_fetch(request.url)
        feed_data = parse_feed(content)
        
        # Determine project name
        project_name = request.project_name or feed_data['title'] or "Feed Import"
        
        # Check if project with same name already exists (for dedupe within same project)
        db_project = db.query(Project).filter(Project.name == project_name).first()
        
        if not db_project:
            # Create new project
            db_project = Project(
                name=project_name,
                description=feed_data.get('description'),
                classification=Classification.NORMAL,
                status=ProjectStatus.RESEARCH
            )
            db.add(db_project)
            db.commit()
            db.refresh(db_project)
            
            # Create initial event
            event = ProjectEvent(
                project_id=db_project.id,
                event_type="project_created",
                actor=username,
                event_metadata=_safe_event_metadata({"name": project_name, "source": "feed_import"}, context="audit")
            )
            db.add(event)
            db.commit()
        
        # Create initial event
        event = ProjectEvent(
            project_id=db_project.id,
            event_type="project_created",
            actor=username,
            event_metadata=_safe_event_metadata({"name": project_name, "source": "feed_import"}, context="audit")
        )
        # Process feed items
        created_count = 0
        skipped_duplicates = 0
        items_to_process = feed_data['items'][:request.limit]
        
        for item in items_to_process:
            # Dedupe: check if document with same guid or link already exists in project
            existing_doc = None
            if item['guid']:
                # Check by guid first (PostgreSQL JSONB query)
                from sqlalchemy import func
                existing_doc = db.query(Document).filter(
                    Document.project_id == db_project.id,
                    Document.document_metadata.isnot(None),
                    func.jsonb_extract_path_text(Document.document_metadata, 'item_guid') == item['guid']
                ).first()
            
            if not existing_doc and item['link']:
                # Check by link if guid didn't match
                existing_doc = db.query(Document).filter(
                    Document.project_id == db_project.id,
                    Document.document_metadata.isnot(None),
                    func.jsonb_extract_path_text(Document.document_metadata, 'item_link') == item['link']
                ).first()
            
            if existing_doc:
                skipped_duplicates += 1
                continue
            
            # Build raw content
            published_str = item['published'] or ''
            raw_content = f"{item['title']}\n{published_str}\n{item['link']}\n\n{item['summary_text']}"
            
            # Run ingest pipeline (same as document upload)
            normalized_text = normalize_text(raw_content)
            
            # Progressive sanitization pipeline
            pii_gate_reasons = {}
            sanitize_level = SanitizeLevel.NORMAL
            usage_restrictions = {"ai_allowed": True, "export_allowed": True}
            masked_text = None
            
            # Try normal masking
            masked_text = mask_text(normalized_text, level="normal")
            is_safe, reasons = pii_gate_check(masked_text)
            if is_safe:
                sanitize_level = SanitizeLevel.NORMAL
                pii_gate_reasons = None
            else:
                pii_gate_reasons["normal"] = reasons
                
                # Try strict masking
                masked_text = mask_text(normalized_text, level="strict")
                is_safe, reasons = pii_gate_check(masked_text)
                if is_safe:
                    sanitize_level = SanitizeLevel.STRICT
                    usage_restrictions = {"ai_allowed": True, "export_allowed": True}
                else:
                    pii_gate_reasons["strict"] = reasons
                    
                    # Use paranoid masking
                    masked_text = mask_text(normalized_text, level="paranoid")
                    is_safe, reasons = pii_gate_check(masked_text)
                    
                    if not is_safe:
                        # This should never happen - paranoid must guarantee gate pass
                        logger.error(f"Paranoid masking failed PII gate for feed item: {item['guid']}")
                        continue  # Skip this item
                    
                    sanitize_level = SanitizeLevel.PARANOID
                    usage_restrictions = {"ai_allowed": False, "export_allowed": False}
            
            # Create a temporary file (required by Document model)
            file_id = str(uuid.uuid4())
            temp_txt_path = UPLOAD_DIR / f"{file_id}.txt"
            try:
                with open(temp_txt_path, 'w', encoding='utf-8') as f:
                    f.write(raw_content)
            except Exception as e:
                logger.error(f"Failed to create temp file for feed item: {str(e)}")
                continue
            
            # Move to permanent location
            permanent_path = UPLOAD_DIR / f"{file_id}.txt"
            try:
                shutil.move(str(temp_txt_path), str(permanent_path))
            except Exception as e:
                logger.error(f"Failed to move temp file: {str(e)}")
                if temp_txt_path.exists():
                    os.remove(temp_txt_path)
                continue
            
            # Create document with metadata
            guid_short = item['guid'][:8] if item['guid'] else str(uuid.uuid4())[:8]
            db_document = Document(
                project_id=db_project.id,
                filename=f"feed_item_{guid_short}.txt",
                file_type="txt",
                classification=db_project.classification,
                masked_text=masked_text,
                file_path=str(permanent_path),
                sanitize_level=sanitize_level,
                usage_restrictions=usage_restrictions,
                pii_gate_reasons=pii_gate_reasons if pii_gate_reasons else None,
                document_metadata={
                    "source_type": "feed",
                    "feed_url": request.url,
                    "item_guid": item['guid'],
                    "item_link": item['link'],
                    "published": item['published']
                }
            )
            db.add(db_document)
            created_count += 1
        
        db.commit()
        
        # Log import event (metadata only)
        import_event = ProjectEvent(
            project_id=db_project.id,
            event_type="feed_imported",
            actor=username,
            event_metadata=_safe_event_metadata({
                "feed_url": request.url,
                "created_count": created_count,
                "skipped_duplicates": skipped_duplicates,
                "limit": request.limit
            }, context="audit")
        )
        db.add(import_event)
        db.commit()
        
        logger.info(f"Feed import completed: project_id={db_project.id}, created={created_count}, skipped={skipped_duplicates}")
        
        return CreateProjectFromFeedResponse(
            project_id=db_project.id,
            created_count=created_count,
            skipped_duplicates=skipped_duplicates
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Feed import failed: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to import feed: {str(e)}")
