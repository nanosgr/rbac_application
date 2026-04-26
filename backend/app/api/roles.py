import json
from math import ceil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session
from app.db.database import get_db
from app.services.crud import role_service
from app.services.audit_service import audit_service
from app.models.models import User, Role, RoleRead, RoleCreate, RoleUpdate
from app.schemas.schemas import RolePermissionAssignment, PaginatedResponse
from app.core.deps import (
    require_role_read,
    require_role_create,
    require_role_update,
    require_role_delete,
)

router = APIRouter()


def _get_request_meta(request: Request) -> tuple:
    rid = getattr(request.state, "request_id", None)
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return rid, ua, ip


@router.get("/", response_model=PaginatedResponse[RoleRead])
def read_roles(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=1000),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role_read()),
):
    total = role_service.count_roles(db, search=search, is_active=is_active)
    items = role_service.get_roles(db, skip=(page - 1) * size, limit=size, search=search, is_active=is_active)
    role_reads = [RoleRead.model_validate(r) for r in items]
    return PaginatedResponse(items=role_reads, total=total, page=page, size=size, pages=ceil(total / size) if total else 1)


@router.post("/", response_model=RoleRead)
def create_role(
    request: Request,
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role_create()),
):
    if role_service.get_role_by_name(db, name=role.name):
        raise HTTPException(status_code=400, detail="Role name already exists")
    result = role_service.create_role(db=db, role=role)
    rid, ua, ip = _get_request_meta(request)
    audit_service.log(db, action="create", resource="role", resource_id=result.id,
                      user_id=current_user.id, username=current_user.username,
                      after_data=json.dumps({"name": result.name, "description": result.description}),
                      ip=ip, request_id=rid, user_agent=ua)
    return result


@router.get("/{role_id}", response_model=RoleRead)
def read_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role_read()),
):
    db_role = role_service.get_role(db, role_id=role_id)
    if db_role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return db_role


@router.put("/{role_id}", response_model=RoleRead)
def update_role(
    request: Request,
    role_id: int,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role_update()),
):
    target = role_service.get_role(db, role_id=role_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Role not found")
    if role_update.name:
        existing = role_service.get_role_by_name(db, name=role_update.name)
        if existing and existing.id != role_id:
            raise HTTPException(status_code=400, detail="Role name already exists")
    before = json.dumps({"name": target.name, "description": target.description, "is_active": target.is_active})
    result = role_service.update_role(db, role_id, role_update)
    rid, ua, ip = _get_request_meta(request)
    audit_service.log(db, action="update", resource="role", resource_id=role_id,
                      user_id=current_user.id, username=current_user.username,
                      before_data=before,
                      after_data=json.dumps(role_update.model_dump(exclude_unset=True)),
                      ip=ip, request_id=rid, user_agent=ua)
    return result


@router.delete("/{role_id}")
def delete_role(
    request: Request,
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role_delete()),
):
    target = role_service.get_role(db, role_id)
    before = json.dumps({"name": target.name if target else None})
    if not role_service.delete_role(db, role_id):
        raise HTTPException(status_code=404, detail="Role not found")
    rid, ua, ip = _get_request_meta(request)
    audit_service.log(db, action="delete", resource="role", resource_id=role_id,
                      user_id=current_user.id, username=current_user.username,
                      before_data=before,
                      ip=ip, request_id=rid, user_agent=ua)
    return {"message": "Role deleted successfully"}


@router.post("/{role_id}/permissions", response_model=RoleRead)
def assign_permissions_to_role(
    request: Request,
    role_id: int,
    permission_assignment: RolePermissionAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role_update()),
):
    if permission_assignment.role_id != role_id:
        raise HTTPException(status_code=400, detail="Role ID in path and body must match")
    target = role_service.get_role(db, role_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Role not found")
    before = json.dumps({"permission_ids": [p.id for p in target.permissions]})
    updated_role = role_service.assign_permissions_to_role(db, role_id, permission_assignment.permission_ids)
    rid, ua, ip = _get_request_meta(request)
    audit_service.log(db, action="assign_permissions", resource="role", resource_id=role_id,
                      user_id=current_user.id, username=current_user.username,
                      before_data=before,
                      after_data=json.dumps({"permission_ids": permission_assignment.permission_ids}),
                      ip=ip, request_id=rid, user_agent=ua)
    return updated_role
