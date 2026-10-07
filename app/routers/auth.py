from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Response, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import smtplib
from email.message import EmailMessage
from app.database import get_db
from app.config import settings
from app.models.user import User, UserRole, VerificationToken
from app.services.auth import AuthService, get_current_user
import secrets
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["Identity & RBAC"])

class MagicLinkRequest(BaseModel):
    email: EmailStr
    full_name: str | None = "Unknown"

def send_magic_link_email(email: str, link: str):
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            msg = EmailMessage()
            msg.set_content(f"""Click the link below to securely sign into AgentForge:

{link}

This link expires in 15 minutes.""")
            msg['Subject'] = 'Your AgentForge Magic Link'
            msg['From'] = settings.SMTP_FROM
            msg['To'] = email

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            print(f"?? MAGIC LINK EMAIL SENT TO: {email} VIA SMTP")
        except Exception as e:
            print(f"?? ERROR SENDING EMAIL TO {email}: {e}")
            print("=" * 60)
            print(f"?? MAGIC LINK FALLBACK: {link}")
            print("=" * 60)
    else:
        print("=" * 60)
        print(f"?? SMTP NOT CONFIGURED. MOCK EMAIL SENT TO: {email}")
        print(f"?? MAGIC LINK: {link}")
        print("=" * 60)

@router.post("/magic-link")
async def request_magic_link(
    payload: MagicLinkRequest, 
    request: Request,
    background_tasks: BackgroundTasks, 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new unverified user
        user = User(
            email=payload.email,
            hashed_password="magic_link_no_pass",
            full_name=payload.full_name or payload.email.split("@")[0],
            department="General",
            role=UserRole.CREATOR,
            is_verified=False
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Generate token
    raw_token = secrets.token_urlsafe(32)
    hashed_token = AuthService.hash_api_key(raw_token)
    
    # Store token in DB
    v_token = VerificationToken(
        email=payload.email,
        token_hash=hashed_token,
        expires_at=datetime.utcnow() + timedelta(minutes=15)
    )
    db.add(v_token)
    await db.commit()
    
    # Construct link (Using request.base_url to get the host)
    base_url = str(request.base_url).rstrip("/")
    magic_link = f"{base_url}/api/v1/auth/verify?token={raw_token}&email={payload.email}"
    
    # Send email asynchronously
    background_tasks.add_task(send_magic_link_email, payload.email, magic_link)
    
    return {"message": "If the email is valid, a magic link has been sent."}

@router.get("/verify")
async def verify_magic_link(token: str, email: str, response: Response, db: AsyncSession = Depends(get_db)):
    hashed_token = AuthService.hash_api_key(token)
    
    # Check token validity
    result = await db.execute(
        select(VerificationToken)
        .where(VerificationToken.email == email)
        .where(VerificationToken.token_hash == hashed_token)
    )
    v_token = result.scalar_one_or_none()
    
    if not v_token or v_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")
        
    # Get user
    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Mark user verified
    if not user.is_verified:
        user.is_verified = True
    
    # Delete token
    await db.delete(v_token)
    await db.commit()
    
    # Generate JWT
    jwt_token = AuthService.create_access_token(user)
    
    # Set Cookie and redirect
    redirect = RedirectResponse(url="/studio", status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key="access_token", 
        value=f"Bearer {jwt_token}", 
        httponly=True, 
        secure=settings.ENV == 'production',
        samesite="lax",
        max_age=12*60*60
    )
    return redirect

@router.post("/logout")
async def logout():
    redirect = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    redirect.delete_cookie("access_token")
    return redirect

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {"id": str(user.id), "email": user.email, "role": user.role.value, "department": user.department, "full_name": user.full_name}