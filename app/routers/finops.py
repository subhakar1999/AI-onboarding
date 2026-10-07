from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.billing import UsageRecord
from app.models.agent import Agent

router = APIRouter(prefix="/finops", tags=["FinOps & Chargeback"])

@router.get("/summary")
async def get_finops_summary(db: AsyncSession = Depends(get_db)):
    # Global spend aggregation
    total_spend = await db.scalar(select(func.coalesce(func.sum(Agent.current_spend_usd), 0)))
    total_budget = await db.scalar(select(func.coalesce(func.sum(Agent.monthly_budget_usd), 0)))
    total_tokens = await db.scalar(select(func.coalesce(func.sum(UsageRecord.total_tokens), 0)))
    
    # Department chargeback distribution
    dept_stmt = select(
        UsageRecord.cost_center,
        func.sum(UsageRecord.cost_usd).label("spend"),
        func.sum(UsageRecord.total_tokens).label("tokens")
    ).group_by(UsageRecord.cost_center)
    
    dept_results = (await db.execute(dept_stmt)).all()
    
    return {
        "total_spend_usd": float(total_spend),
        "total_budget_usd": float(total_budget),
        "total_tokens_consumed": int(total_tokens),
        "cost_centers": [
            {"department": row[0], "spend_usd": float(row[1]), "tokens": int(row[2])}
            for row in dept_results
        ]
    }