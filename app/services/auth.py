import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, Security, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.models.agent import Agent
from app.models.tenant import TenantProject
from urllib.parse import urlparse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(user: User) -> str:
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "department": user.department,
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def generate_agent_api_key() -> tuple[str, str]:
        """Returns (raw_key, hashed_key). The raw key is shown only once."""
        raw_key = f"af_live_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return raw_key, key_hash

    @staticmethod
    def hash_api_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

# RBAC Dependencies
async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = None
    if credentials:
        token = credentials.credentials
    elif "access_token" in request.cookies:
        cookie_val = request.cookies["access_token"]
        if cookie_val.startswith("Bearer "):
            token = cookie_val.split(" ")[1]
            
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session token")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User disabled or not found")
    return user

def require_roles(allowed_roles: List[UserRole]):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of the following roles: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker

# Dual Connectivity: Accepts JWT User OR External Agent API Key (Bearer af_live_...)
async def get_authenticated_agent_caller(
    agent_id: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: AsyncSession = Depends(get_db)
):
    token = None
    if credentials:
        token = credentials.credentials
    elif "access_token" in request.cookies:
        cookie_val = request.cookies["access_token"]
        if cookie_val.startswith("Bearer "):
            token = cookie_val.split(" ")[1]
            
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization credentials required")

    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    # Path A: External Agent API Key
    if token.startswith("af_live_"):
        incoming_hash = AuthService.hash_api_key(token)
        
        # 1. Check if it's a Tenant-Scoped API Key (Enforces Origin Locking)
        tenant_result = await db.execute(select(TenantProject).where(TenantProject.api_key_hash == incoming_hash))
        tenant = tenant_result.scalar_one_or_none()
        
        if tenant:
            # Enforce Dynamic Origin Whitelist
            origin = request.headers.get("origin") or request.headers.get("referer")
            if origin:
                parsed_origin = urlparse(origin)
                domain_clean = parsed_origin.netloc or parsed_origin.path
                if tenant.registered_domain != domain_clean:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin blocked by Tenant CORS policy")
            
            # Ensure the agent belongs to this tenant's owner
            if agent.owner_id != tenant.user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent does not belong to this Tenant")
                
            return {"caller_type": "TENANT_API_KEY", "user_id": str(tenant.user_id), "department": agent.department, "agent": agent}
            
        # 2. Fallback to Agent-Specific API Key
        elif agent.api_key_hash == incoming_hash:
            return {"caller_type": "AGENT_API_KEY", "user_id": str(agent.owner_id), "department": agent.department, "agent": agent}
            
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

    # Path B: Interactive Dashboard User (JWT)
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User session invalid")
        return {"caller_type": "USER_SESSION", "user_id": str(user.id), "department": user.department, "agent": agent}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session credentials")