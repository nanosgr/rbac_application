"""Motor de decisión RBAC.

Lógica pura de autorización (sin dependencias de FastAPI), inspirada en el ACL de
`simple-rbac`:

- **Jerarquía de roles**: un rol hereda los permisos de todos sus ancestros (DAG).
- **Wildcards de recurso**: los patrones `"users:*"`, `"*:read"` y `"*:*"` matchean.
- **Reglas DENY**: una regla con `effect="deny"` gana siempre sobre cualquier allow.
- **Assertions**: una regla con `assertion` otorga sólo si el predicado (evaluado en
  runtime con el contexto del endpoint) devuelve True.
- **Resultado ternario**: `evaluate()` devuelve `True` (permitido) / `False`
  (denegado) / `None` (ninguna regla aplica).

El pegamento con FastAPI (dependencias, request) vive en `app.core.deps`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Set, Tuple

from cachetools import TTLCache
from sqlmodel import Session, select

from app.core.assertions import run_assertion
from app.models.models import Permission, Role, RolePermissionLink, User

# Cache de políticas efectivas: key=(username, token_version), value=(user_id, EffectivePolicy)
POLICY_CACHE_TTL = 60
_policy_cache: TTLCache = TTLCache(maxsize=512, ttl=POLICY_CACHE_TTL)


@dataclass
class EffectivePolicy:
    """Conjunto de reglas efectivas de un usuario, ya resueltas sobre su jerarquía de roles."""

    allow: Set[str] = field(default_factory=set)
    deny: Set[str] = field(default_factory=set)
    # (patrón "resource:action", nombre de assertion) -> allow condicional
    conditional: List[Tuple[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "allow": sorted(self.allow),
            "deny": sorted(self.deny),
            "conditional": [{"pattern": p, "assertion": a} for p, a in self.conditional],
        }


# ---------------------------------------------------------------------------
# Resolución de jerarquía de roles
# ---------------------------------------------------------------------------

def resolve_role_family(role: Role, _seen: Optional[Set[int]] = None) -> Iterator[Role]:
    """Itera `role` y todos sus ancestros (padres, abuelos, ...) sin repetir.

    Cycle-safe: un ciclo accidental en `role_parents` no produce recursión infinita.
    Equivale a `get_family`/`get_parents` de `simple-rbac/rbac/acl.py`.
    """
    if _seen is None:
        _seen = set()
    key = id(role) if role.id is None else role.id
    if key in _seen:
        return
    _seen.add(key)
    yield role
    for parent in role.parents or []:
        yield from resolve_role_family(parent, _seen)


def effective_role_ids(user: User) -> Set[int]:
    """IDs de todos los roles activos que aportan permisos al usuario (directos + heredados)."""
    ids: Set[int] = set()
    for role in user.roles:
        for r in resolve_role_family(role):
            if r.is_active and r.id is not None:
                ids.add(r.id)
    return ids


# ---------------------------------------------------------------------------
# Construcción de la política efectiva
# ---------------------------------------------------------------------------

def build_policy(db: Session, user: User) -> EffectivePolicy:
    """Arma la `EffectivePolicy` del usuario consultando las reglas `role_permissions`."""
    if user.is_superuser:
        return EffectivePolicy(allow={"*:*"})

    role_ids = effective_role_ids(user)
    policy = EffectivePolicy()
    if not role_ids:
        return policy

    rows = db.exec(
        select(RolePermissionLink, Permission)
        .join(Permission, Permission.id == RolePermissionLink.permission_id)
        .where(RolePermissionLink.role_id.in_(role_ids))
        .where(Permission.is_active == True)  # noqa: E712
    ).all()

    for link, perm in rows:
        pattern = f"{perm.resource}:{perm.action}"
        if link.assertion:
            policy.conditional.append((pattern, link.assertion))
        elif link.effect == "deny":
            policy.deny.add(pattern)
        else:
            policy.allow.add(pattern)

    return policy


# ---------------------------------------------------------------------------
# Evaluación
# ---------------------------------------------------------------------------

def pattern_matches(pattern: str, resource: str, action: str) -> bool:
    """`pattern` ("resource:action" con `*` opcional) matchea el par pedido."""
    p_resource, _, p_action = pattern.partition(":")
    return p_resource in (resource, "*") and p_action in (action, "*")


def evaluate(
    policy: EffectivePolicy,
    resource: str,
    action: str,
    *,
    user: Optional[User] = None,
    context: Optional[dict] = None,
) -> Optional[bool]:
    """Resultado ternario: True permitido / False denegado / None sin regla aplicable.

    DENY se evalúa primero y gana de inmediato (como en `simple-rbac`).
    """
    for pattern in policy.deny:
        if pattern_matches(pattern, resource, action):
            return False

    for pattern in policy.allow:
        if pattern_matches(pattern, resource, action):
            return True

    for pattern, assertion in policy.conditional:
        if pattern_matches(pattern, resource, action) and run_assertion(assertion, user, context):
            return True

    return None


# alias con el nombre de simple-rbac
is_allowed = evaluate


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def cache_key(user: User) -> Tuple[str, int]:
    return (user.username, user.token_version)


def get_cached_policy(db: Session, user: User) -> EffectivePolicy:
    """Devuelve la política del usuario desde el cache; la construye y cachea en miss."""
    key = cache_key(user)
    cached = _policy_cache.get(key)
    if cached is not None:
        return cached[1]
    policy = build_policy(db, user)
    _policy_cache[key] = (user.id, policy)
    return policy


def invalidate_policy_cache() -> None:
    """Limpia el cache de políticas.

    Se llama al mutar el grafo rol/permiso/jerarquía. En despliegues multi-worker
    cada proceso tiene su propio cache; el TTL de 60s es el backstop entre workers.
    """
    _policy_cache.clear()
