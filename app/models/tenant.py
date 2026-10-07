import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import String, DateTime, Boolean, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class ProjectStatus(str, Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    LIVE = "LIVE"
    SUSPENDED = "SUSPENDED"

class TenantProject(Base):
    __tablename__ = "tenant_projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Domains and CORS
    project_name: Mapped[str] = mapped_column(String(100), nullable=False)
    registered_domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    
    # API Key & Security
    api_key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    
    # Status
    status: Mapped[ProjectStatus] = mapped_column(SQLEnum(ProjectStatus), default=ProjectStatus.PENDING_VERIFICATION, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    owner = relationship("User", backref="projects")
