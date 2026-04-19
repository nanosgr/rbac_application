import json
from math import ceil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session
from app.db.database import get_db
from app.services.crud import user_service
from app.services.audit_service import audit_service
from app.models.models import User, UserRead, UserCreate, UserUpdate
from app.schemas.schemas import UserRoleAssignment, PaginatedResponse, UserProfileUpdate, PasswordChange
from app.core.deps import (
    get_current_active_user,
    require_user_read,
    require_user_create,
    require_user_update,
    require_user_delete,
)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[UserRead])
def read_users(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=1000),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_read()),
):
    total = user_service.count_users(db, search=search, is_active=is_active)
    items = user_service.get_users(db, skip=(page - 1) * size, limit=size, search=search, is_active=is_active)
    user_reads = [UserRead.model_validate(u) for u in items]
    return PaginatedResponse(items=user_reads, total=total, page=page, size=size, pages=ceil(total / size) if total else 1)


@router.post("/", response_model=UserRead)
def create_user(
    request: Request,
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_create()),
):
    if user_service.get_user_by_username(db, username=user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    if user_service.get_user_by_email(db, email=user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    result = user_service.create_user(db=db, user=user)
    audit_service.log(db, action="create", resource="user", resource_id=result.id,
                      user_id=current_user.id, username=current_user.username,
                      details=json.dumps({"username": result.username, "email": result.email}),
                      ip=request.client.host if request.client else None)
    return result


@router.get("/me", response_model=UserRead)
def read_user_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.put("/me", response_model=UserRead)
def update_user_me(
    request: Request,
    profile_update: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if profile_update.email:
        existing = user_service.get_user_by_email(db, email=profile_update.email)
        if existing and existing.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email already taken")
    update = UserUpdate(**profile_update.model_dump(exclude_unset=True))
    result = user_service.update_user(db, current_user.id, update)
    audit_service.log(db, action="update", resource="user", resource_id=current_user.id,
                      user_id=current_user.id, username=current_user.username,
                      details=json.dumps(profile_update.model_dump(exclude_unset=True)),
                      ip=request.client.host if request.client else None)
    return result


@router.put("/me/password")
def change_password_me(
    request: Request,
    password_data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not user_service.change_password(db, current_user.id, password_data.current_password, password_data.new_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    audit_service.log(db, action="password_change", resource="user", resource_id=current_user.id,
                      user_id=current_user.id, username=current_user.username,
                      ip=request.client.host if request.client else None)
    return {"message": "Password updated successfully"}


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_read()),
):
    db_user = user_service.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    request: Request,
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_update()),
):
    if user_service.get_user(db, user_id=user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user_update.username:
        existing = user_service.get_user_by_username(db, username=user_update.username)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=400, detail="Username already taken")
    if user_update.email:
        existing = user_service.get_user_by_email(db, email=user_update.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=400, detail="Email already taken")
    result = user_service.update_user(db, user_id, user_update)
    audit_service.log(db, action="update", resource="user", resource_id=user_id,
                      user_id=current_user.id, username=current_user.username,
                      details=json.dumps(user_update.model_dump(exclude_unset=True, exclude={"password"})),
                      ip=request.client.host if request.client else None)
    return result


@router.delete("/{user_id}")
def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_delete()),
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own user account")
    target = user_service.get_user(db, user_id)
    if not user_service.delete_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    audit_service.log(db, action="delete", resource="user", resource_id=user_id,
                      user_id=current_user.id, username=current_user.username,
                      details=json.dumps({"deleted_username": target.username if target else None}),
                      ip=request.client.host if request.client else None)
    return {"message": "User deleted successfully"}


@router.post("/{user_id}/roles", response_model=UserRead)
def assign_roles_to_user(
    request: Request,
    user_id: int,
    role_assignment: UserRoleAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_update()),
):
    if role_assignment.user_id != user_id:
        raise HTTPException(status_code=400, detail="User ID in path and body must match")
    updated_user = user_service.assign_roles_to_user(db, user_id, role_assignment.role_ids)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    audit_service.log(db, action="assign_roles", resource="user", resource_id=user_id,
                      user_id=current_user.id, username=current_user.username,
                      details=json.dumps({"role_ids": role_assignment.role_ids}),
                      ip=request.client.host if request.client else None)
    return updated_user
