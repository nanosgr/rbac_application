from typing import List, Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func
from pydantic import EmailStr


# ---------------------------------------------------------------------------
# Tablas de asociación (link models con table=True)
# ---------------------------------------------------------------------------

class UserRoleLink(SQLModel, table=True):
    __tablename__ = "user_roles"

    user_id: Optional[int] = Field(default=None, foreign_key="users.id", primary_key=True)
    role_id: Optional[int] = Field(default=None, foreign_key="roles.id", primary_key=True)
    assigned_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


class RolePermissionLink(SQLModel, table=True):
    __tablename__ = "role_permissions"

    role_id: Optional[int] = Field(default=None, foreign_key="roles.id", primary_key=True)
    permission_id: Optional[int] = Field(default=None, foreign_key="permissions.id", primary_key=True)
    assigned_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


# ---------------------------------------------------------------------------
# Permission
# ---------------------------------------------------------------------------

class PermissionBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    resource: str
    action: str
    is_active: bool = True


class Permission(PermissionBase, table=True):
    __tablename__ = "permissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )
    roles: List["Role"] = Relationship(back_populates="permissions", link_model=RolePermissionLink, sa_relationship_kwargs={"lazy": "selectin"})


class PermissionCreate(PermissionBase):
    pass


class PermissionRead(PermissionBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PermissionUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------

class RoleBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    is_active: bool = True


class Role(RoleBase, table=True):
    __tablename__ = "roles"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )
    users: List["User"] = Relationship(back_populates="roles", link_model=UserRoleLink, sa_relationship_kwargs={"lazy": "selectin"})
    permissions: List[Permission] = Relationship(back_populates="roles", link_model=RolePermissionLink, sa_relationship_kwargs={"lazy": "selectin"})


class RoleCreate(RoleBase):
    pass


class RoleRead(RoleBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    permissions: List[PermissionRead] = []


class RoleUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: EmailStr = Field(index=True, unique=True)
    full_name: Optional[str] = None
    is_active: bool = True


class User(UserBase, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    is_superuser: bool = False
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )
    roles: List[Role] = Relationship(back_populates="users", link_model=UserRoleLink, sa_relationship_kwargs={"lazy": "selectin"})


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int
    is_superuser: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    roles: List[RoleRead] = []


class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    username: Optional[str] = None
    action: str
    resource: str
    resource_id: Optional[int] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


# Resolver referencias circulares
Permission.model_rebuild()
Role.model_rebuild()
User.model_rebuild()
RoleRead.model_rebuild()
UserRead.model_rebuild()
