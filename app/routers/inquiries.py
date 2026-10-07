from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from app.database import get_db
from app.models.inquiry import ProductInquiry
from app.models.user import User, UserRole
from app.services.auth import require_roles

router = APIRouter(prefix="/inquiries", tags=["Product Inquiries & Feedback"])

class InquiryCreate(BaseModel):
    name: str
    email: EmailStr
    department: Optional[str] = "General"
    category: str = "PRODUCT_INFO" # FEATURE_REQUEST, ENTERPRISE_SUPPORT, SALES
    message: str

@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_inquiry(payload: InquiryCreate, db: AsyncSession = Depends(get_db)):
    inquiry = ProductInquiry(**payload.model_dump())
    db.add(inquiry)
    await db.commit()
    await db.refresh(inquiry)
    return {"message": "Thank you. Your request has been recorded. Our enterprise team will follow up.", "inquiry_id": str(inquiry.id)}

@router.get("", dependencies=[Depends(require_roles([UserRole.ADMIN]))])
async def list_inquiries(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProductInquiry).order_by(ProductInquiry.created_at.desc()))
    return result.scalars().all()