import uuid
import secrets
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.tenant import TenantProject, ProjectStatus
from app.models.user import User
from app.services.auth import get_current_user, AuthService

router = APIRouter(prefix="/projects", tags=["Service Request & Control Plane"])

class ProjectCreateRequest(BaseModel):
    project_name: str
    domain: str

class ProjectResponse(BaseModel):
    id: str
    project_name: str
    registered_domain: str
    status: str
    api_key: str | None = None  # Only returned on creation

@router.post("/", response_model=ProjectResponse)
async def create_tenant_project(
    payload: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Domain Validation (Basic SSRF / Origin Check)
    domain_clean = payload.domain.strip().lower()
    if domain_clean.startswith("http://") or domain_clean.startswith("https://"):
        parsed = urlparse(domain_clean)
        domain_clean = parsed.netloc or parsed.path
    
    # Check if domain is already registered
    existing = await db.execute(select(TenantProject).where(TenantProject.registered_domain == domain_clean))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Domain is already registered to a project.")

    # Generate Ephemeral/Tenant-Scoped API Key
    raw_api_key = f"af_live_{secrets.token_urlsafe(32)}"
    api_key_hash = AuthService.hash_api_key(raw_api_key)

    project = TenantProject(
        user_id=user.id,
        project_name=payload.project_name,
        registered_domain=domain_clean,
        api_key_hash=api_key_hash,
        status=ProjectStatus.PENDING_VERIFICATION
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        id=str(project.id),
        project_name=project.project_name,
        registered_domain=project.registered_domain,
        status=project.status.value,
        api_key=raw_api_key  # Show once!
    )

@router.get("/", response_model=list[ProjectResponse])
async def list_tenant_projects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(select(TenantProject).where(TenantProject.user_id == user.id))
    projects = result.scalars().all()
    
    return [
        ProjectResponse(
            id=str(p.id),
            project_name=p.project_name,
            registered_domain=p.registered_domain,
            status=p.status.value,
            api_key=None
        ) for p in projects
    ]
