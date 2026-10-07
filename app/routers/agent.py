from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List, Optional
from app.database import get_db
from app.models.agent import Agent
from app.models.billing import UsageRecord
from app.schemas.agent import AgentCreate, AgentResponse
from app.models.user import User, UserRole
from app.services.auth import require_roles, AuthService, get_current_user
from app.services.runtime import AgentExecutionRuntime

router = APIRouter(prefix="/agents", tags=["Agent Management & Portals"])

class PortalExecuteRequest(BaseModel):
    message: str

class PublicAgentInfo(BaseModel):
    id: str
    name: str
    department: str
    model_name: str
    status: str

@router.get("", response_model=List[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    return result.scalars().all()

@router.get("/{agent_id}/public", response_model=PublicAgentInfo)
async def get_public_agent_info(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return PublicAgentInfo(
        id=str(agent.id),
        name=agent.name,
        department=agent.department,
        model_name=agent.model_name,
        status=agent.status
    )

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles([UserRole.ADMIN, UserRole.CREATOR]))
):
    raw_api_key, key_hash = AuthService.generate_agent_api_key()
    
    agent = Agent(
        **payload.model_dump(),
        owner_id=user.id,
        api_key_hash=key_hash
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    data = agent.__dict__.copy()
    data["raw_api_key"] = raw_api_key
    return data

@router.post("/{agent_id}/regenerate-key")
async def regenerate_agent_api_key(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    agent = await db.get(Agent, agent_id)
    if not agent or agent.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found or access unauthorized")
    
    raw_api_key, key_hash = AuthService.generate_agent_api_key()
    agent.api_key_hash = key_hash
    await db.commit()

    return {
        "status": "SUCCESS",
        "agent_id": str(agent.id),
        "raw_api_key": raw_api_key,
        "message": "Store this key safely; it will not be displayed again."
    }

@router.post("/{agent_id}/portal/execute")
async def execute_portal_chat(
    agent_id: UUID,
    payload: PortalExecuteRequest,
    db: AsyncSession = Depends(get_db)
):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent.status == "PAUSED":
        raise HTTPException(status_code=403, detail="This agent is currently paused by the administrator.")
    if agent.hard_stop_on_breach and agent.current_spend_usd >= agent.monthly_budget_usd:
        agent.status = "CIRCUIT_BROKEN"
        await db.commit()
        raise HTTPException(status_code=402, detail="Agent budget reached. Service temporarily paused.")

    class SimpleMsg:
        def __init__(self, content):
            self.role = "user"
            self.content = content

    messages = [SimpleMsg(payload.message)]
    exec_result = await AgentExecutionRuntime.run(agent=agent, user_messages=messages, db=db)

    # Record usage in ledger
    usage_entry = UsageRecord(
        agent_id=agent.id,
        user_id=str(agent.owner_id),
        cost_center=agent.department,
        model_name=agent.model_name,
        prompt_tokens=exec_result["prompt_tokens"],
        completion_tokens=exec_result["completion_tokens"],
        total_tokens=exec_result["total_tokens"],
        latency_ms=exec_result["latency_ms"],
        cost_usd=exec_result["cost_usd"]
    )
    agent.current_spend_usd += exec_result["cost_usd"]
    db.add(usage_entry)
    await db.commit()

    return {
        "reply": exec_result["output_text"],
        "cost_usd": float(exec_result["cost_usd"]),
        "latency_ms": exec_result["latency_ms"]
    }