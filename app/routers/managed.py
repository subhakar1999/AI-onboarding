import uuid
import secrets
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.provisioning import ManagedServiceRequest, ProjectStatus
from app.models.user import User
from app.services.auth import get_current_user
from app.services.verification import verify_widget_installation

router = APIRouter(prefix="/managed", tags=["Service Provisioning & Control Plane"])

class ProjectCreateRequest(BaseModel):
    project_name: str
    domain: str

class ProjectResponse(BaseModel):
    id: str
    project_name: str
    registered_domain: str
    status: str
    public_widget_key: str

@router.post("/", response_model=ProjectResponse)
async def create_managed_project(
    payload: ProjectCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Domain Validation (Basic SSRF / Origin Check)
    domain_clean = payload.domain.strip().lower()
    if domain_clean.startswith("http://") or domain_clean.startswith("https://"):
        parsed = urlparse(domain_clean)
        domain_clean = parsed.netloc or parsed.path
    
    # Check if domain is already registered
    existing = await db.execute(select(ManagedServiceRequest).where(ManagedServiceRequest.registered_domain == domain_clean))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Domain is already registered to a project.")

    # Generate Ephemeral/Tenant-Scoped Public API Key for Widget
    public_widget_key = f"af_pub_{secrets.token_urlsafe(32)}"

    project = ManagedServiceRequest(
        user_id=user.id,
        project_name=payload.project_name,
        registered_domain=domain_clean,
        public_widget_key=public_widget_key,
        status=ProjectStatus.PENDING_VERIFICATION
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Queue background verification
    background_tasks.add_task(verify_widget_installation, str(project.id))

    return ProjectResponse(
        id=str(project.id),
        project_name=project.project_name,
        registered_domain=project.registered_domain,
        status=project.status.value,
        public_widget_key=project.public_widget_key
    )

@router.get("/", response_model=list[ProjectResponse])
async def list_managed_projects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(select(ManagedServiceRequest).where(ManagedServiceRequest.user_id == user.id))
    projects = result.scalars().all()
    
    return [
        ProjectResponse(
            id=str(p.id),
            project_name=p.project_name,
            registered_domain=p.registered_domain,
            status=p.status.value,
            public_widget_key=p.public_widget_key
        ) for p in projects
    ]

class WidgetExecuteRequest(BaseModel):
    widget_key: str
    message: str

@router.post("/widget/execute")
async def execute_widget(
    payload: WidgetExecuteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Retrieve Origin header
    origin = request.headers.get("origin")
    if not origin:
        raise HTTPException(status_code=403, detail="Missing Origin header.")
    
    parsed_origin = urlparse(origin)
    origin_domain = parsed_origin.netloc or parsed_origin.path

    # Verify widget_key and domain
    result = await db.execute(
        select(ManagedServiceRequest).where(
            ManagedServiceRequest.public_widget_key == payload.widget_key
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=401, detail="Invalid widget key.")
        
    if project.registered_domain != origin_domain:
        raise HTTPException(status_code=403, detail=f"Origin {origin_domain} not allowed for this widget.")
        
    if project.status != ProjectStatus.LIVE:
        raise HTTPException(status_code=403, detail="Service is not active or pending verification.")

    # In a real implementation, you would trigger the LLM/Agent execution here.
    # For now, returning a mock response.
    return {
        "reply": f"AgentForge Assistant: I received your message '{payload.message}'. My identity is verified for domain {project.registered_domain}."
    }
