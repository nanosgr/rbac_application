"""Tests del alcance de datos (data scoping): motor + API end-to-end.

- Unit: `resolve_scope`, `Scope.matches`, `Scope.apply` (SQLite in-memory).
- e2e: `GET/POST /api/v1/orders` con roles scope `all` / `own` / `attribute` y DENY.
"""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.core import rbac
from app.core.rbac import EffectivePolicy, Scope, resolve_scope
from app.core.security import create_access_token
from app.db.database import get_db
from app.main import app
from app.models.models import Order, Permission, Role, RolePermissionLink, User, UserScope
from app.services.crud import user_service


@pytest.fixture(autouse=True)
def _clear_cache():
    rbac.invalidate_policy_cache()
    yield
    rbac.invalidate_policy_cache()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _token(user: User) -> dict:
    tok = create_access_token({"sub": user.username, "token_version": user.token_version})
    return {"Authorization": f"Bearer {tok}"}


# ===========================================================================
# Unit: resolve_scope
# ===========================================================================

def _u(uid=1):
    return SimpleNamespace(id=uid)


def test_resolve_scope_engine_all():
    s = resolve_scope(EffectivePolicy(allow={"orders:read"}), "orders", "read", _u())
    assert s.granted and s.allow_all and not s.denied


def test_resolve_scope_engine_deny_wins():
    p = EffectivePolicy(allow={"orders:read"}, deny={"orders:*"})
    s = resolve_scope(p, "orders", "read", _u())
    assert s.denied and not s.allow_all


def test_resolve_scope_engine_superuser_wildcard():
    s = resolve_scope(EffectivePolicy(allow={"*:*"}), "orders", "read", _u())
    assert s.allow_all


def test_resolve_scope_engine_own():
    p = EffectivePolicy(scoped=[("orders:read", "own", None)])
    s = resolve_scope(p, "orders", "read", _u(5))
    assert s.granted and s.include_own and not s.allow_all and s.owner_id == 5


def test_resolve_scope_engine_attribute():
    p = EffectivePolicy(
        scoped=[("orders:read", "attribute", "warehouse")],
        scope_values={"warehouse": {"norte", "sur"}},
    )
    s = resolve_scope(p, "orders", "read", _u())
    assert s.dimension == "warehouse" and s.values == {"norte", "sur"}


def test_resolve_scope_engine_combines_own_and_attribute():
    p = EffectivePolicy(
        scoped=[
            ("orders:read", "own", None),
            ("orders:read", "attribute", "warehouse"),
        ],
        scope_values={"warehouse": {"norte"}},
    )
    s = resolve_scope(p, "orders", "read", _u(9))
    assert s.include_own and s.dimension == "warehouse" and s.values == {"norte"}


def test_resolve_scope_engine_no_rule_not_granted():
    s = resolve_scope(EffectivePolicy(), "orders", "read", _u())
    assert not s.granted and not s.denied


def test_resolve_scope_engine_attribute_without_values_is_empty():
    p = EffectivePolicy(scoped=[("orders:read", "attribute", "warehouse")])
    s = resolve_scope(p, "orders", "read", _u())
    assert s.granted and s.is_empty


# ===========================================================================
# Unit: Scope.matches
# ===========================================================================

def test_scope_matches_own_and_attribute():
    own = Scope(owner_id=3, granted=True, include_own=True)
    assert own.matches(SimpleNamespace(owner_id=3, warehouse="x"))
    assert not own.matches(SimpleNamespace(owner_id=9, warehouse="x"))

    attr = Scope(owner_id=3, granted=True, dimension="warehouse", values={"norte"})
    assert attr.matches(SimpleNamespace(owner_id=9, warehouse="norte"))
    assert not attr.matches(SimpleNamespace(owner_id=9, warehouse="sur"))


def test_scope_matches_all_and_denied():
    assert Scope(granted=True, allow_all=True).matches(SimpleNamespace(owner_id=1, warehouse="z"))
    assert not Scope(granted=True, denied=True).matches(SimpleNamespace(owner_id=1))
    assert not Scope(granted=False).matches(SimpleNamespace(owner_id=1))


# ===========================================================================
# Unit: Scope.apply (SQLite)
# ===========================================================================

def _seed_orders(db):
    u1 = User(username="s1", email="s1@e.com", hashed_password="x")
    u2 = User(username="s2", email="s2@e.com", hashed_password="x")
    db.add_all([u1, u2])
    db.commit()
    db.refresh(u1)
    db.refresh(u2)
    db.add_all([
        Order(customer="a", total=1, status="pending", warehouse="norte", owner_id=u1.id),
        Order(customer="b", total=1, status="pending", warehouse="sur", owner_id=u1.id),
        Order(customer="c", total=1, status="pending", warehouse="norte", owner_id=u2.id),
    ])
    db.commit()
    return u1, u2


def _customers(db, scope):
    rows = db.exec(scope.apply(select(Order), Order).order_by(Order.id)).all()
    return {r.customer for r in rows}


def test_scope_apply_own(db):
    u1, _ = _seed_orders(db)
    assert _customers(db, Scope(owner_id=u1.id, granted=True, include_own=True)) == {"a", "b"}


def test_scope_apply_attribute(db):
    _, u2 = _seed_orders(db)
    scope = Scope(owner_id=u2.id, granted=True, dimension="warehouse", values={"norte"})
    assert _customers(db, scope) == {"a", "c"}


def test_scope_apply_own_or_attribute(db):
    u1, _ = _seed_orders(db)
    scope = Scope(owner_id=u1.id, granted=True, include_own=True,
                  dimension="warehouse", values={"norte"})
    assert _customers(db, scope) == {"a", "b", "c"}


def test_scope_apply_all_and_empty(db):
    _seed_orders(db)
    assert _customers(db, Scope(granted=True, allow_all=True)) == {"a", "b", "c"}
    assert _customers(db, Scope(owner_id=1, granted=True, dimension="warehouse", values=set())) == set()


# ===========================================================================
# e2e API
# ===========================================================================

@pytest.fixture
def orders_graph(db):
    perms = {
        n: Permission(name=n, resource="orders", action=n.split(":")[1])
        for n in ["orders:read", "orders:create", "orders:update", "orders:delete"]
    }
    star = Permission(name="*:*", resource="*", action="*")
    db.add_all([*perms.values(), star])
    db.commit()
    for p in [*perms.values(), star]:
        db.refresh(p)

    vendedor = Role(name="Vendedor")
    jefe = Role(name="Jefe")
    admin = Role(name="AdminOrders")
    blocked = Role(name="Blocked")
    db.add_all([vendedor, jefe, admin, blocked])
    db.commit()
    for r in (vendedor, jefe, admin, blocked):
        db.refresh(r)

    db.add_all([
        RolePermissionLink(role_id=vendedor.id, permission_id=perms["orders:read"].id, scope="own"),
        RolePermissionLink(role_id=vendedor.id, permission_id=perms["orders:create"].id, scope="own"),
        RolePermissionLink(role_id=jefe.id, permission_id=perms["orders:read"].id,
                           scope="attribute", scope_dimension="warehouse"),
        RolePermissionLink(role_id=admin.id, permission_id=star.id),
        RolePermissionLink(role_id=blocked.id, permission_id=star.id),
        RolePermissionLink(role_id=blocked.id, permission_id=perms["orders:read"].id, effect="deny"),
    ])
    db.commit()

    def mkuser(name, role):
        u = User(username=name, email=f"{name}@e.com", hashed_password="x")
        u.roles.append(role)
        db.add(u)
        db.commit()
        db.refresh(u)
        return user_service.get_user(db, u.id)

    users = {
        "vendedor": mkuser("vend", vendedor),
        "vendedor2": mkuser("vend2", vendedor),
        "jefe": mkuser("jefe", jefe),
        "admin": mkuser("admino", admin),
        "blocked": mkuser("blk", blocked),
    }

    db.add(UserScope(user_id=users["jefe"].id, dimension="warehouse", value="norte"))
    db.add_all([
        Order(customer="A", total=10, status="pending", warehouse="norte", owner_id=users["vendedor"].id),
        Order(customer="B", total=20, status="paid", warehouse="sur", owner_id=users["vendedor"].id),
        Order(customer="C", total=30, status="pending", warehouse="norte", owner_id=users["vendedor2"].id),
        Order(customer="D", total=40, status="paid", warehouse="centro", owner_id=users["vendedor2"].id),
    ])
    db.commit()
    return users


def _list_customers(client, user):
    r = client.get("/api/v1/orders/", headers=_token(user))
    assert r.status_code == 200, r.text
    body = r.json()
    return body, {it["customer"] for it in body["items"]}


def test_scope_own_lists_only_own_orders(client, orders_graph):
    body, customers = _list_customers(client, orders_graph["vendedor"])
    assert customers == {"A", "B"}
    assert body["total"] == 2


def test_scope_attribute_lists_only_dimension_orders(client, orders_graph):
    body, customers = _list_customers(client, orders_graph["jefe"])
    assert customers == {"A", "C"}  # warehouse == "norte"
    assert body["total"] == 2


def test_scope_all_lists_everything(client, orders_graph):
    body, customers = _list_customers(client, orders_graph["admin"])
    assert customers == {"A", "B", "C", "D"}
    assert body["total"] == 4


def test_deny_rule_blocks_with_403(client, orders_graph):
    r = client.get("/api/v1/orders/", headers=_token(orders_graph["blocked"]))
    assert r.status_code == 403


def test_object_level_out_of_scope_is_404(client, orders_graph):
    # el pedido "C" es del vendedor2; el vendedor no debe verlo
    all_orders = client.get("/api/v1/orders/", headers=_token(orders_graph["admin"])).json()["items"]
    cid = next(o["id"] for o in all_orders if o["customer"] == "C")
    own = next(o["id"] for o in all_orders if o["customer"] == "A")

    assert client.get(f"/api/v1/orders/{cid}", headers=_token(orders_graph["vendedor"])).status_code == 404
    assert client.get(f"/api/v1/orders/{own}", headers=_token(orders_graph["vendedor"])).status_code == 200


def test_create_sets_owner_and_appears_in_own_list(client, orders_graph):
    r = client.post("/api/v1/orders/", headers=_token(orders_graph["vendedor"]),
                    json={"customer": "Nuevo", "total": 5, "warehouse": "centro"})
    assert r.status_code == 200, r.text
    assert r.json()["owner_id"] == orders_graph["vendedor"].id
    _, customers = _list_customers(client, orders_graph["vendedor"])
    assert customers == {"A", "B", "Nuevo"}


def test_role_permission_rules_endpoint_exposes_scope(client, orders_graph, db):
    from app.models.models import Role
    vendedor = db.exec(select(Role).where(Role.name == "Vendedor")).one()
    r = client.get(f"/api/v1/roles/{vendedor.id}/permissions", headers=_token(orders_graph["admin"]))
    assert r.status_code == 200, r.text
    rules = r.json()
    assert {rule["scope"] for rule in rules} == {"own"}
    assert all(rule["effect"] == "allow" for rule in rules)


def test_effective_permissions_endpoint_includes_scoped(client, orders_graph, db):
    from app.models.models import Role
    jefe = db.exec(select(Role).where(Role.name == "Jefe")).one()
    r = client.get(f"/api/v1/roles/{jefe.id}/effective-permissions", headers=_token(orders_graph["admin"]))
    assert r.status_code == 200, r.text
    scoped = r.json()["scoped"]
    assert any(s["pattern"] == "orders:read" and s["scope"] == "attribute"
               and s["dimension"] == "warehouse" for s in scoped)


def test_updating_user_scopes_changes_visibility(client, orders_graph, db):
    _, before = _list_customers(client, orders_graph["jefe"])
    assert before == {"A", "C"}

    r = client.put(
        f"/api/v1/users/{orders_graph['jefe'].id}/scopes",
        headers=_token(orders_graph["admin"]),
        json={"items": [{"dimension": "warehouse", "value": "norte"},
                        {"dimension": "warehouse", "value": "centro"}]},
    )
    assert r.status_code == 200, r.text

    _, after = _list_customers(client, orders_graph["jefe"])
    assert after == {"A", "C", "D"}  # ahora también "centro"
