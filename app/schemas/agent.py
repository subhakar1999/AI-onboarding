import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    department: str
    status: str = "ACTIVE"
    model_name: str = "gpt-4o"
    system_prompt: str
    temperature: Decimal = Field(default=Decimal("0.20"), max_digits=3, decimal_places=2)
    tools_enabled: List[Dict[str, Any]] = Field(default_factory=list)
    enable_pii_shield: bool = True
    monthly_budget_usd: Decimal = Field(default=Decimal("100.00"), max_digits=10, decimal_places=2)
    hard_stop_on_breach: bool = True
    alert_threshold_pct: int = 80

class AgentCreate(AgentBase):
    pass

class AgentResponse(AgentBase):
    id: uuid.UUID
    current_spend_usd: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)