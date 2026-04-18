from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from app.db.database import get_db
from app.core.security import create_access_token
from app.core.config import settings
from app.core.deps import get_current_active_user
from app.models.models import User
from app.services.crud import user_service
from app.services.audit_service import audit_service
from app.schemas.schemas import Token, UserLogin

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = user_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    audit_service.log(db, action="login", resource="auth",
                      user_id=user.id, username=user.username,
                      ip=request.client.host if request.client else None)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    audit_service.log(db, action="logout", resource="auth",
                      user_id=current_user.id, username=current_user.username,
                      ip=request.client.host if request.client else None)
    return {"message": "Logged out successfully"}


@router.post("/login-json", response_model=Token)
async def login_json(
    request: Request,
    user_credentials: UserLogin,
    db: Session = Depends(get_db),
):
    user = user_service.authenticate_user(db, user_credentials.username, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    audit_service.log(db, action="login", resource="auth",
                      user_id=user.id, username=user.username,
                      ip=request.client.host if request.client else None)
    return {"access_token": access_token, "token_type": "bearer"}
