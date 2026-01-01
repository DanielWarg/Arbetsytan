from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import uuid
import shutil
import logging
from typing import Optional, List
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from database import get_db, engine
from models import Project, ProjectEvent, Document, Base, Classification, SanitizeLevel
from schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectEventCreate, ProjectEventResponse,
    DocumentResponse, DocumentListResponse
)
from text_processing import (
    extract_text_from_pdf, extract_text_from_txt,
    normalize_text, mask_text, validate_file_type, pii_gate_check, PiiGateError,
    transcribe_audio, normalize_transcript_text, process_transcript
)

# Create tables
Base.metadata.create_all(bind=engine)

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Arbetsytan API")

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
        event_metadata={"name": project.name}
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
            event_metadata={"changes": changes}
        )
        db.add(event)
        db.commit()
    
    return project


@app.delete("/api/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_basic_auth)
):
    """Delete a project and all its documents and events (permanent)"""
    import os
    from pathlib import Path
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get all documents for this project to delete files
    documents = db.query(Document).filter(Document.project_id == project_id).all()
    document_count = len(documents)
    
    # Delete document files from disk
    deleted_files = 0
    for doc in documents:
        if doc.file_path:
            file_path = UPLOAD_DIR / doc.file_path
            try:
                if file_path.exists():
                    os.remove(file_path)
                    deleted_files += 1
            except Exception:
                # Ignore errors (file might already be deleted)
                pass
    
    # Delete events first (explicit cascade)
    db.query(ProjectEvent).filter(ProjectEvent.project_id == project_id).delete()
    # Delete documents (cascade should handle, but explicit for safety)
    db.query(Document).filter(Document.project_id == project_id).delete()
    # Delete project
    db.delete(project)
    db.commit()
    
    # Log only IDs and counts (no filenames or content)
    # Note: In production, use proper logging, not print
    print(f"Deleted project {project_id} with {document_count} documents ({deleted_files} files removed from disk)")
    
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
        event_metadata=event.metadata
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
            event_metadata={"filename": file.filename, "file_type": file_type}
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
            event_metadata=event_metadata
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

