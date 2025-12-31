from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from typing import Optional, List

from database import get_db, engine
from models import Project, ProjectEvent, Base
from schemas import ProjectCreate, ProjectResponse, ProjectEventCreate, ProjectEventResponse

# Create tables
Base.metadata.create_all(bind=engine)

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
        classification=project.classification
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

