from datetime import datetime
from typing import Optional
from sqlmodel import Session, select, func
from app.models.models import AuditLog


class AuditService:
    def log(
        self,
        db: Session,
        action: str,
        resource: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        resource_id: Optional[int] = None,
        details: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> None:
        entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
            ip_address=ip,
        )
        db.add(entry)
        db.commit()

    def get_logs(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 50,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ):
        query = select(AuditLog)
        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource:
            query = query.where(AuditLog.resource == resource)
        if from_date:
            query = query.where(AuditLog.timestamp >= from_date)
        if to_date:
            query = query.where(AuditLog.timestamp <= to_date)
        return db.exec(query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)).all()

    def count_logs(
        self,
        db: Session,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> int:
        query = select(func.count(AuditLog.id))
        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource:
            query = query.where(AuditLog.resource == resource)
        if from_date:
            query = query.where(AuditLog.timestamp >= from_date)
        if to_date:
            query = query.where(AuditLog.timestamp <= to_date)
        return db.exec(query).one()


audit_service = AuditService()
