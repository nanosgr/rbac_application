import json
from math import ceil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session
from app.db.database import get_db
from app.services.crud import order_service
from app.services.audit_service import audit_service
from app.models.models import OrderRead, OrderCreate, OrderUpdate
from app.schemas.schemas import PaginatedResponse
from app.core.deps import require_scope, ScopedAccess

router = APIRouter()


def _get_request_meta(request: Request) -> tuple:
    rid = getattr(request.state, "request_id", None)
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return rid, ua, ip


@router.get("/", response_model=PaginatedResponse[OrderRead])
def read_orders(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=1000),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    access: ScopedAccess = Depends(require_scope("orders", "read")),
):
    """Lista los pedidos que el alcance del usuario permite ver (all / own / attribute)."""
    total = order_service.count(db, access.scope, status=status)
    items = order_service.list(
        db, access.scope, skip=(page - 1) * size, limit=size, status=status
    )
    return PaginatedResponse(
        items=[OrderRead.model_validate(o) for o in items],
        total=total, page=page, size=size,
        pages=ceil(total / size) if total else 1,
    )


@router.post("/", response_model=OrderRead)
def create_order(
    request: Request,
    order: OrderCreate,
    db: Session = Depends(get_db),
    access: ScopedAccess = Depends(require_scope("orders", "create")),
):
    result = order_service.create(db, order, owner_id=access.user.id)
    rid, ua, ip = _get_request_meta(request)
    audit_service.log(db, action="create", resource="order", resource_id=result.id,
                      user_id=access.user.id, username=access.user.username,
                      after_data=json.dumps({"customer": result.customer, "warehouse": result.warehouse}),
                      ip=ip, request_id=rid, user_agent=ua)
    return result


@router.get("/{order_id}", response_model=OrderRead)
def read_order(
    order_id: int,
    db: Session = Depends(get_db),
    access: ScopedAccess = Depends(require_scope("orders", "read")),
):
    order = order_service.get(db, order_id)
    if order is None or not access.scope.matches(order):
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/{order_id}", response_model=OrderRead)
def update_order(
    request: Request,
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db),
    access: ScopedAccess = Depends(require_scope("orders", "update")),
):
    order = order_service.get(db, order_id)
    if order is None or not access.scope.matches(order):
        raise HTTPException(status_code=404, detail="Order not found")
    before = json.dumps({"customer": order.customer, "total": order.total,
                         "status": order.status, "warehouse": order.warehouse})
    result = order_service.update(db, order_id, order_update)
    rid, ua, ip = _get_request_meta(request)
    audit_service.log(db, action="update", resource="order", resource_id=order_id,
                      user_id=access.user.id, username=access.user.username,
                      before_data=before,
                      after_data=json.dumps(order_update.model_dump(exclude_unset=True)),
                      ip=ip, request_id=rid, user_agent=ua)
    return result


@router.delete("/{order_id}")
def delete_order(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    access: ScopedAccess = Depends(require_scope("orders", "delete")),
):
    order = order_service.get(db, order_id)
    if order is None or not access.scope.matches(order):
        raise HTTPException(status_code=404, detail="Order not found")
    before = json.dumps({"customer": order.customer, "warehouse": order.warehouse})
    order_service.delete(db, order_id)
    rid, ua, ip = _get_request_meta(request)
    audit_service.log(db, action="delete", resource="order", resource_id=order_id,
                      user_id=access.user.id, username=access.user.username,
                      before_data=before, ip=ip, request_id=rid, user_agent=ua)
    return {"message": "Order deleted successfully"}
