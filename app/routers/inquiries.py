from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from app.database import get_db
from app.models.inquiry import ProductInquiry
from app.models.user import User, UserRole
from app.services.auth import get_current_user, require_roles

router = APIRouter(prefix="/inquiries", tags=["Product Inquiries & Leads Capture"])

class InquiryCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    agent_id: Optional[UUID] = None
    department: Optional[str] = "General"
    category: str = "PRODUCT_INFO" # FEATURE_REQUEST, ENTERPRISE_SUPPORT, SALES, LEAD
    message: str

class InquiryResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str]
    agent_id: Optional[str]
    department: Optional[str]
    category: str
    message: str
    status: str
    created_at: str

@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_inquiry(payload: InquiryCreate, db: AsyncSession = Depends(get_db)):
    inquiry = ProductInquiry(**payload.model_dump())
    db.add(inquiry)
    await db.commit()
    await db.refresh(inquiry)
    return {
        "message": "Thank you! Your request has been recorded.",
        "inquiry_id": str(inquiry.id)
    }

@router.post("/capture", status_code=status.HTTP_201_CREATED)
async def capture_agent_lead(payload: InquiryCreate, db: AsyncSession = Depends(get_db)):
    data = payload.model_dump()
    data["category"] = "LEAD"
    inquiry = ProductInquiry(**data)
    db.add(inquiry)
    await db.commit()
    await db.refresh(inquiry)
    return {
        "status": "SUCCESS",
        "message": "Lead captured successfully.",
        "lead_id": str(inquiry.id)
    }

@router.get("", response_model=List[InquiryResponse])
async def list_all_inquiries(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(select(ProductInquiry).order_by(ProductInquiry.created_at.desc()))
    records = result.scalars().all()
    return [
        InquiryResponse(
            id=str(r.id),
            name=r.name,
            email=r.email,
            phone=r.phone,
            agent_id=str(r.agent_id) if r.agent_id else None,
            department=r.department,
            category=r.category,
            message=r.message,
            status=r.status,
            created_at=r.created_at.strftime("%Y-%m-%d %H:%M")
        )
        for r in records
    ]

@router.get("/agent/{agent_id}", response_model=List[InquiryResponse])
async def list_agent_leads(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(ProductInquiry)
        .where(ProductInquiry.agent_id == agent_id)
        .order_by(ProductInquiry.created_at.desc())
    )
    records = result.scalars().all()
    return [
        InquiryResponse(
            id=str(r.id),
            name=r.name,
            email=r.email,
            phone=r.phone,
            agent_id=str(r.agent_id) if r.agent_id else None,
            department=r.department,
            category=r.category,
            message=r.message,
            status=r.status,
            created_at=r.created_at.strftime("%Y-%m-%d %H:%M")
        )
        for r in records
    ]