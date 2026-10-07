from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.database import get_db
from app.models.agent import Agent
from app.models.billing import UsageRecord
from app.schemas.execution import ExecuteRequest, ExecuteResponse
from app.services.runtime import AgentExecutionRuntime
from app.services.auth import get_authenticated_agent_caller

router = APIRouter(prefix="/agents", tags=["Agent Execution"])

# In app/routers/execution.py, update the endpoint signature:
@router.post("/{agent_id}/execute", response_model=ExecuteResponse)
async def execute_agent(
    agent_id: UUID,
    payload: ExecuteRequest,
    caller_ctx: dict = Depends(get_authenticated_agent_caller),
    db: AsyncSession = Depends(get_db)
):
    agent = caller_ctx["agent"]
    user_id = caller_ctx["user_id"]
    department = caller_ctx["department"]
    
    # Enforce Budget & Hard-Stop
    if agent.status == "PAUSED":
        raise HTTPException(status_code=403, detail="Agent is paused by administrator")
    if agent.hard_stop_on_breach and agent.current_spend_usd >= agent.monthly_budget_usd:
        agent.status = "CIRCUIT_BROKEN"
        await db.commit()
        raise HTTPException(status_code=402, detail="Agent monthly budget breached.")

    exec_result = await AgentExecutionRuntime.run(agent=agent, user_messages=payload.messages)

    # Save to FinOps ledger
    usage_entry = UsageRecord(
        agent_id=agent.id,
        user_id=user_id,
        cost_center=department,
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

    return ExecuteResponse(
        response=exec_result["output_text"],
        latency_ms=exec_result["latency_ms"],
        prompt_tokens=exec_result["prompt_tokens"],
        completion_tokens=exec_result["completion_tokens"],
        total_tokens=exec_result["total_tokens"],
        cost_usd=float(exec_result["cost_usd"]),
        budget_exhausted=(agent.current_spend_usd >= agent.monthly_budget_usd)
    )