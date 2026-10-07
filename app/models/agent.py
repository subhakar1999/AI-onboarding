import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Text, Boolean, DateTime, Numeric, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(128), nullable=True, unique=True, index=True)
    owner = relationship("User", back_populates="agents")
    
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    department: Mapped[str] = mapped_column(String(64), nullable=False) # FinOps cost-center
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False) # ACTIVE, PAUSED, CIRCUIT_BROKEN
    
    # Model Configuration
    model_name: Mapped[str] = mapped_column(String(64), default="gpt-4o", nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    temperature: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0.20, nullable=False)
    
    # Capabilities & Knowledge
    tools_enabled: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    enable_pii_shield: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # FinOps & Guardrail Budgeting
    monthly_budget_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=100.00, nullable=False)
    current_spend_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=0.000000, nullable=False)
    hard_stop_on_breach: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alert_threshold_pct: Mapped[int] = mapped_column(Numeric(3, 0), default=80, nullable=False)
    

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    usage_records = relationship("UsageRecord", back_populates="agent", cascade="all, delete-orphan")