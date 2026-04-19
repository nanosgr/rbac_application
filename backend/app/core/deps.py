from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session
from typing import List
from app.db.database import get_db
from app.core.security import verify_token
from app.services.crud import user_service
from app.models.models import User

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    username = verify_token(credentials.credentials)
    if username is None:
        raise credentials_exception
    user = user_service.get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_permissions(required_permissions: List[str]):
    def permission_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.is_superuser:
            return current_user

        user_permissions = [
            f"{permission.resource}:{permission.action}"
            for role in current_user.roles
            if role.is_active
            for permission in role.permissions
            if permission.is_active
        ]

        for required in required_permissions:
            if required not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required: {required}",
                )
        return current_user

    return permission_checker


def require_user_read():
    return require_permissions(["users:read"])

def require_user_create():
    return require_permissions(["users:create"])

def require_user_update():
    return require_permissions(["users:update"])

def require_user_delete():
    return require_permissions(["users:delete"])

def require_role_read():
    return require_permissions(["roles:read"])

def require_role_create():
    return require_permissions(["roles:create"])

def require_role_update():
    return require_permissions(["roles:update"])

def require_role_delete():
    return require_permissions(["roles:delete"])

def require_permission_read():
    return require_permissions(["permissions:read"])

def require_permission_create():
    return require_permissions(["permissions:create"])

def require_permission_update():
    return require_permissions(["permissions:update"])

def require_permission_delete():
    return require_permissions(["permissions:delete"])
