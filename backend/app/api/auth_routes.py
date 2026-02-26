"""JWT Authentication routes — register, login, me."""
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models.orm_models import User, Role, Tenant

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "changethis_use_a_real_secret_in_production_64chars")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""
    tenant_name: str = "Madinat Al Saada Aluminium & Glass Works LLC"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
    tenant_id: str
    full_name: str = ""


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Get or create tenant
    tenant_result = await db.execute(select(Tenant).where(Tenant.name == req.tenant_name))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        tenant = Tenant(name=req.tenant_name)
        db.add(tenant)
        await db.flush()

    # Get Admin role (created by seed data)
    role_result = await db.execute(select(Role).where(Role.name == "Admin"))
    role = role_result.scalar_one_or_none()

    user = User(
        email=req.email,
        hashed_password=pwd_context.hash(req.password),
        full_name=req.full_name,
        tenant_id=tenant.id,
        role_id=role.id if role else None,
    )
    db.add(user)
    await db.flush()

    role_name = role.name if role else "Admin"
    token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "tenant_id": tenant.id,
        "role": role_name,
    })
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        role=role_name,
        tenant_id=tenant.id,
        full_name=req.full_name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    role_name = "Viewer"
    if user.role_id:
        role_result = await db.execute(select(Role).where(Role.id == user.role_id))
        role = role_result.scalar_one_or_none()
        if role:
            role_name = role.name

    token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "tenant_id": user.tenant_id or "",
        "role": role_name,
    })
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        role=role_name,
        tenant_id=user.tenant_id or "",
        full_name=user.full_name or "",
    )


@router.get("/me")
async def get_me(db: AsyncSession = Depends(get_db)):
    """Returns current user — actual auth handled by deps.get_current_user."""
    return {"message": "Use Authorization: Bearer <token> header and call with get_current_user dep"}
