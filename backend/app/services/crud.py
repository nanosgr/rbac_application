from sqlmodel import Session, select, func, or_
from sqlalchemy import select as sa_select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.models import User, Role, Permission, UserCreate, UserUpdate, RoleCreate, RoleUpdate, PermissionCreate, PermissionUpdate
from app.core.security import get_password_hash, verify_password


class UserService:
    def get_user(self, db: Session, user_id: int) -> Optional[User]:
        stmt = sa_select(User).options(selectinload(User.roles).selectinload(Role.permissions)).where(User.id == user_id)
        return db.execute(stmt).scalars().first()

    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        return db.exec(select(User).where(User.username == username)).first()

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.exec(select(User).where(User.email == email)).first()

    def get_users(self, db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None, is_active: Optional[bool] = None) -> List[User]:
        stmt = sa_select(User).options(selectinload(User.roles).selectinload(Role.permissions))
        if search:
            stmt = stmt.where(or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
            ))
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        return list(db.execute(stmt.offset(skip).limit(limit)).scalars().unique().all())

    def count_users(self, db: Session, search: Optional[str] = None, is_active: Optional[bool] = None) -> int:
        query = select(func.count(User.id))
        if search:
            query = query.where(or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
            ))
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        return db.exec(query).one()

    def create_user(self, db: Session, user: UserCreate) -> User:
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=get_password_hash(user.password),
            full_name=user.full_name,
            is_active=user.is_active,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def update_user(self, db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
        db_user = self.get_user(db, user_id)
        if db_user:
            update_data = user_update.model_dump(exclude_unset=True)
            if "password" in update_data:
                update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
            for field, value in update_data.items():
                setattr(db_user, field, value)
            db.commit()
            db.refresh(db_user)
        return db_user

    def delete_user(self, db: Session, user_id: int) -> bool:
        db_user = self.get_user(db, user_id)
        if db_user:
            db.delete(db_user)
            db.commit()
            return True
        return False

    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[User]:
        user = self.get_user_by_username(db, username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def change_password(self, db: Session, user_id: int, current_password: str, new_password: str) -> bool:
        db_user = self.get_user(db, user_id)
        if not db_user or not verify_password(current_password, db_user.hashed_password):
            return False
        db_user.hashed_password = get_password_hash(new_password)
        db.commit()
        return True

    def assign_roles_to_user(self, db: Session, user_id: int, role_ids: List[int]) -> Optional[User]:
        db_user = self.get_user(db, user_id)
        if db_user:
            roles = db.exec(select(Role).where(Role.id.in_(role_ids))).all()
            db_user.roles = roles
            db.commit()
        return self.get_user(db, user_id)


class RoleService:
    def get_role(self, db: Session, role_id: int) -> Optional[Role]:
        stmt = sa_select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
        return db.execute(stmt).scalars().first()

    def get_role_by_name(self, db: Session, name: str) -> Optional[Role]:
        return db.exec(select(Role).where(Role.name == name)).first()

    def get_roles(self, db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None, is_active: Optional[bool] = None) -> List[Role]:
        stmt = sa_select(Role).options(selectinload(Role.permissions))
        if search:
            stmt = stmt.where(or_(
                Role.name.ilike(f"%{search}%"),
                Role.description.ilike(f"%{search}%"),
            ))
        if is_active is not None:
            stmt = stmt.where(Role.is_active == is_active)
        return list(db.execute(stmt.offset(skip).limit(limit)).scalars().unique().all())

    def count_roles(self, db: Session, search: Optional[str] = None, is_active: Optional[bool] = None) -> int:
        query = select(func.count(Role.id))
        if search:
            query = query.where(or_(
                Role.name.ilike(f"%{search}%"),
                Role.description.ilike(f"%{search}%"),
            ))
        if is_active is not None:
            query = query.where(Role.is_active == is_active)
        return db.exec(query).one()

    def create_role(self, db: Session, role: RoleCreate) -> Role:
        db_role = Role(**role.model_dump())
        db.add(db_role)
        db.commit()
        db.refresh(db_role)
        return db_role

    def update_role(self, db: Session, role_id: int, role_update: RoleUpdate) -> Optional[Role]:
        db_role = self.get_role(db, role_id)
        if db_role:
            update_data = role_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_role, field, value)
            db.commit()
            db.refresh(db_role)
        return db_role

    def delete_role(self, db: Session, role_id: int) -> bool:
        db_role = self.get_role(db, role_id)
        if db_role:
            db.delete(db_role)
            db.commit()
            return True
        return False

    def assign_permissions_to_role(self, db: Session, role_id: int, permission_ids: List[int]) -> Optional[Role]:
        db_role = self.get_role(db, role_id)
        if db_role:
            permissions = db.exec(select(Permission).where(Permission.id.in_(permission_ids))).all()
            db_role.permissions = permissions
            db.commit()
        return self.get_role(db, role_id)


class PermissionService:
    def get_permission(self, db: Session, permission_id: int) -> Optional[Permission]:
        return db.get(Permission, permission_id)

    def get_permission_by_name(self, db: Session, name: str) -> Optional[Permission]:
        return db.exec(select(Permission).where(Permission.name == name)).first()

    def get_permissions(self, db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None, is_active: Optional[bool] = None, resource: Optional[str] = None, action: Optional[str] = None) -> List[Permission]:
        query = select(Permission)
        if search:
            query = query.where(or_(
                Permission.name.ilike(f"%{search}%"),
                Permission.description.ilike(f"%{search}%"),
            ))
        if is_active is not None:
            query = query.where(Permission.is_active == is_active)
        if resource:
            query = query.where(Permission.resource == resource)
        if action:
            query = query.where(Permission.action == action)
        return db.exec(query.offset(skip).limit(limit)).all()

    def count_permissions(self, db: Session, search: Optional[str] = None, is_active: Optional[bool] = None, resource: Optional[str] = None, action: Optional[str] = None) -> int:
        query = select(func.count(Permission.id))
        if search:
            query = query.where(or_(
                Permission.name.ilike(f"%{search}%"),
                Permission.description.ilike(f"%{search}%"),
            ))
        if is_active is not None:
            query = query.where(Permission.is_active == is_active)
        if resource:
            query = query.where(Permission.resource == resource)
        if action:
            query = query.where(Permission.action == action)
        return db.exec(query).one()

    def create_permission(self, db: Session, permission: PermissionCreate) -> Permission:
        db_permission = Permission(**permission.model_dump())
        db.add(db_permission)
        db.commit()
        db.refresh(db_permission)
        return db_permission

    def update_permission(self, db: Session, permission_id: int, permission_update: PermissionUpdate) -> Optional[Permission]:
        db_permission = self.get_permission(db, permission_id)
        if db_permission:
            update_data = permission_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_permission, field, value)
            db.commit()
            db.refresh(db_permission)
        return db_permission

    def delete_permission(self, db: Session, permission_id: int) -> bool:
        db_permission = self.get_permission(db, permission_id)
        if db_permission:
            db.delete(db_permission)
            db.commit()
            return True
        return False


user_service = UserService()
role_service = RoleService()
permission_service = PermissionService()
