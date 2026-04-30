from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session
from typing import List, Optional
from cachetools import TTLCache
from app.db.database import get_db
from app.core.security import verify_token
from app.services.crud import user_service
from app.models.models import User

security = HTTPBearer()

# Cache de permisos: key=(username, token_version), TTL=60s
_permissions_cache: TTLCache = TTLCache(maxsize=512, ttl=60)


def get_user_permissions(user: User) -> set:
    """Retorna el conjunto de permisos efectivos del usuario. Superusers obtienen wildcard."""
    if user.is_superuser:
        return {"*:*"}
    return {
        f"{permission.resource}:{permission.action}"
        for role in user.roles
        if role.is_active
        for permission in role.permissions
        if permission.is_active
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    cache_key = (payload["sub"], payload["token_version"])
    cached = _permissions_cache.get(cache_key)

    if cached is not None:
        user_id, _ = cached
        user = user_service.get_user(db, user_id)
        if user is None:
            raise credentials_exception
        return user

    user = user_service.get_user_by_username(db, username=payload["sub"])
    if user is None:
        raise credentials_exception

    if user.token_version != payload["token_version"]:
        raise credentials_exception

    permissions = get_user_permissions(user)
    _permissions_cache[cache_key] = (user.id, permissions)

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_permissions(required_permissions: List[str]):
    def permission_checker(current_user: User = Depends(get_current_active_user)):
        cache_key = (current_user.username, current_user.token_version)
        cached = _permissions_cache.get(cache_key)
        user_permissions = cached[1] if cached else get_user_permissions(current_user)

        for required in required_permissions:
            if "*:*" not in user_permissions and required not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required: {required}",
                )
        return current_user

    return permission_checker


def check_owner_or_permission(resource_owner_id: Optional[int], current_user: User, permission: str) -> bool:
    """Retorna True si el usuario es el dueño del recurso O tiene el permiso especificado."""
    cache_key = (current_user.username, current_user.token_version)
    cached = _permissions_cache.get(cache_key)
    user_permissions = cached[1] if cached else get_user_permissions(current_user)
    if "*:*" in user_permissions or permission in user_permissions:
        return True
    return resource_owner_id is not None and current_user.id == resource_owner_id


def require_owner_or_permission(permission: str):
    """
    Dependencia ABAC: inyecta current_user validado para endpoints donde el acceso
    se permite si el usuario es dueño del recurso O tiene el permiso indicado.

    Uso en el endpoint:
        current_user = Depends(require_owner_or_permission("items:read"))
        if not check_owner_or_permission(item.owner_id, current_user, "items:read"):
            raise HTTPException(403)
    """
    def dependency(current_user: User = Depends(get_current_active_user)) -> User:
        return current_user
    return dependency


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
