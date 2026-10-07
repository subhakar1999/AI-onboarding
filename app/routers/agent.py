from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
from app.database import get_db
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentResponse
from app.models.user import User, UserRole
from app.services.auth import require_roles, AuthService

router = APIRouter(prefix="/agents", tags=["Agent Management"])

@router.get("", response_model=List[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    return result.scalars().all()

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

# In create_agent, attach the logged-in creator and generate the first API key:
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
    
    # Return agent data plus the one-time raw API key for programmatic consumption
    data = agent.__dict__.copy()
    data["raw_api_key"] = raw_api_key
    return data