from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import EmailStr
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


class PaginatedResponse(SQLModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int


class Token(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshTokenRequest(SQLModel):
    refresh_token: str


class UserLogin(SQLModel):
    username: str
    password: str


class UserRoleAssignment(SQLModel):
    user_id: int
    role_ids: List[int]


class RolePermissionRule(SQLModel):
    permission_id: int
    effect: str = "allow"          # "allow" | "deny"
    assertion: Optional[str] = None  # nombre de assertion registrada


class RolePermissionAssignment(SQLModel):
    role_id: int
    permission_ids: List[int] = []
    # si viene, tiene prioridad sobre permission_ids (permite effect/assertion por regla)
    rules: Optional[List[RolePermissionRule]] = None


class RoleParentAssignment(SQLModel):
    role_id: int
    parent_ids: List[int]


class EffectivePermissionsRead(SQLModel):
    role_id: int
    contributing_role_ids: List[int]
    allow: List[str]
    deny: List[str]
    conditional: List[dict]


class UserProfileUpdate(SQLModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class PasswordChange(SQLModel):
    current_password: str
    new_password: str = Field(min_length=8)


class PasswordResetRequest(SQLModel):
    identifier: str  # email o username


class PasswordResetConfirm(SQLModel):
    token: str
    new_password: str = Field(min_length=8)


class AuditLogRead(SQLModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    resource: str
    resource_id: Optional[int] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    status: str = "success"
    before_data: Optional[str] = None
    after_data: Optional[str] = None
    subject_id: Optional[int] = None
    user_agent: Optional[str] = None
    timestamp: Optional[datetime] = None
