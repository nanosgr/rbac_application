# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Role-Based Access Control (RBAC) application with a FastAPI backend and PostgreSQL database. The system implements granular permissions with JWT authentication.

## Development Commands

### Backend (FastAPI)

**Setup:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Run development server:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Or use: ./run_dev.sh
```

**Initialize database (SQLAlchemy):**
```bash
cd backend
python -c "from app.db.init_db import create_tables, init_db; create_tables(); init_db()"
```

**Alembic migrations:**
```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
alembic downgrade -1
```

**Run tests:**
```bash
cd backend
pytest
pytest --cov=app
```

### Scaffold a new CRUD resource

`scripts/scaffold_resource.py` generates a full data model (backend + frontend) from
a YAML spec, following the `orders` reference pattern and its `TEMPLATE:<PLURAL>` sentinel
markers. See `scripts/scaffold/README.md` and `scripts/scaffold/specs/examples/`.

```bash
cd backend && ./venv/bin/pip install -r requirements-dev.txt   # jinja2 + pyyaml (dev only)
python scripts/scaffold_resource.py --from <spec>.yaml --dry-run
python scripts/scaffold_resource.py --from <spec>.yaml
python scripts/remove_domain.py <plural>          # undo (byte-clean round-trip)
python -m pytest scripts/scaffold/tests -q        # generator's own tests
```

`scoping.mode` = `none` / `own` / `attribute`. `Admin`/`Manager` roles auto-inherit new
resources via `init_db.py`. Not yet supported: `date`/`datetime` fields,
`grants.scoped_demo_roles`.

### Database (PostgreSQL)

**Automated setup:**
```bash
cd database
chmod +x setup_database.sh
./setup_database.sh
```

**Manual setup:**
```bash
sudo -u postgres psql
CREATE USER rbac_user WITH PASSWORD 'rbac_password';
CREATE DATABASE rbac_app OWNER rbac_user;
\q
cd database
psql -U rbac_user -d rbac_app -f 01_create_database.sql
# Continue with 02-07 in order
```

**Database connection defaults:**
- Host: localhost:5432
- Database: rbac_app
- User: rbac_user
- Password: rbac_password

## Architecture

### Backend Structure

The backend follows a layered architecture:

- **app/api/** - API endpoints organized by resource (auth, users, roles, permissions)
- **app/core/** - Core functionality (config, security, dependencies, `rbac.py` decision engine, `assertions.py` ABAC predicates)
- **app/models/** - SQLAlchemy ORM models
- **app/schemas/** - Pydantic schemas for validation
- **app/services/** - Business logic and CRUD operations
- **app/db/** - Database configuration and initialization

### RBAC Permission System

**Permission Format:** `resource:action` (e.g., `users:read`, `roles:create`). Wildcards
allowed: `users:*`, `*:read`, `*:*` (matched by `rbac.pattern_matches`).

**Decision engine:** `app/core/rbac.py` (pure, no FastAPI) builds an `EffectivePolicy`
(`allow` / `deny` / `conditional` pattern sets) per user and evaluates it:

- **Role hierarchy:** roles inherit from parent roles (table `role_parents`, DAG,
  cycle-guarded). `rbac.resolve_role_family` walks ancestors; a user's policy is the
  union over every assigned role's family.
- **DENY rules:** `role_permissions.effect` is `"allow"` (default) or `"deny"`. A matching
  `deny` always wins.
- **Assertions:** `role_permissions.assertion` names a predicate registered in
  `app/core/assertions.py` (built-in: `owner`). Evaluated at request time with a
  `context` dict supplied by the endpoint.
- **Data scoping ("which rows"):** `role_permissions.scope` is `"all"` (default),
  `"own"` or `"attribute"` (+ `scope_dimension`, e.g. `"warehouse"`). Values that place
  the user in a dimension live in table `user_scopes` (`user_id, dimension, value`).
  `rbac.resolve_scope(policy, resource, action, user) -> Scope`; the `Scope` object
  filters a query (`scope.apply(stmt, Model)`) and checks a loaded row
  (`scope.matches(row)`). `own` + `attribute` combine as OR; `deny` still wins;
  a plain `allow` (or superuser `*:*`) → `allow_all`.
- **Ternary result:** `rbac.evaluate(...) -> True | False | None`.
- **Cache:** `_policy_cache` (TTL 60s, key `(username, token_version)`); mutations
  (incl. `user_scopes` via `user_scope_service`) call `rbac.invalidate_policy_cache()`.

**Permission Checking:**
1. Superusers get the `{"*:*"}` policy (not a special code path).
2. Regular users inherit permissions from their roles and all ancestor roles.
3. `require_permissions(["users:read"])` — static dependency, no context (assertion-only
   rules do NOT grant here).
4. `has_permission(user, resource, action, *, db, context=...)` — full evaluation
   including assertions; call inside the endpoint body.
5. `require_scope("<resource>", "read")` — dependency returning `ScopedAccess(user, scope)`;
   403 only on `deny` / no rule. The endpoint applies `access.scope` to the query and to
   loaded rows.
<!-- TEMPLATE:ORDERS:START -->
   The reference implementation lives in `app/api/orders.py` (the `orders` domain model).
<!-- TEMPLATE:ORDERS:END -->

**Example endpoint with permissions:**
```python
from app.core.deps import require_permissions, has_permission

@router.get("/users")
def list_users(current_user: User = Depends(require_permissions(["users:read"]))):
    ...

@router.get("/documents/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_active_user)):
    document = ...
    if not has_permission(current_user, "documents", "read", db=db,
                          context={"resource_owner_id": document.owner_id}):
        raise HTTPException(403)
```

**Role hierarchy API:** `POST /api/v1/roles/{id}/parents` (assign parents, 400 on cycle),
`GET /api/v1/roles/{id}/effective-permissions` (resolved allow/deny/conditional/scoped).
`POST /api/v1/roles/{id}/permissions` accepts either `permission_ids` or richer `rules`
(`{permission_id, effect, assertion, scope, scope_dimension}`).

**Scope admin API:** `GET/PUT /api/v1/users/{id}/scopes` and `GET /api/v1/users/me/scopes`
manage a user's `user_scopes` rows (`{items: [{dimension, value}]}`; PUT replaces the set).

**Convenience functions:** Use `require_user_read()`, `require_role_create()`, etc. from `app/core/deps.py` for common permission checks.

**Engine tests:** `cd backend && pytest` (see `tests/test_rbac_engine.py`,
`tests/test_roles_api.py`; SQLite in-memory, no live DB needed).

### Database Schema

The system uses two levels of database abstraction:

1. **PostgreSQL Native (database/ folder):** Complete schema with triggers, stored procedures, and views in the `rbac` schema
2. **SQLAlchemy ORM (backend/app/models/):** Simplified models for the FastAPI application

**Key relationships:**
- Users ↔ Roles (many-to-many via user_roles)
- Roles ↔ Permissions (many-to-many via role_permissions; carries `effect` + `assertion` +
  `scope` / `scope_dimension`)
- Roles ↔ Roles (many-to-many via role_parents; role hierarchy DAG)
- Users → scope values (`user_scopes`: `user_id, dimension, value`)
<!-- TEMPLATE:ORDERS:START -->
- `orders` — reference domain model demonstrating data scoping (`owner_id` for `own`,
  `warehouse` column for `attribute` dimension `"warehouse"`)
<!-- TEMPLATE:ORDERS:END -->

### Authentication Flow

1. Login via POST `/api/v1/auth/login` or `/api/v1/auth/login-json`
2. Receive JWT access token
3. Include token in requests: `Authorization: Bearer <token>`
4. Token verification happens in `app/core/deps.py:get_current_user()`

**Default Users:**
- superadmin/admin123 (Super Admin role)
- admin/admin123 (Admin role)
- manager/manager123 (Manager role)
- user/user123 (User role)

### Configuration

Environment variables are managed via `.env` file (see `.env.example`):
- Database connection settings (POSTGRES_*)
- JWT settings (SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES)
- CORS origins for frontend

Configuration is loaded via Pydantic Settings in `app/core/config.py`.

## Key Design Patterns

**Dependency Injection:** FastAPI's `Depends()` is used throughout for database sessions, authentication, and authorization.

**Permission Inheritance:** Users inherit all permissions from their assigned roles. The `require_permissions()` function collects permissions from all active roles assigned to a user.

**Database Sessions:** Always use `db: Session = Depends(get_db)` to get database sessions. Sessions are automatically closed after the request.

**Password Hashing:** Passwords are hashed using bcrypt via `passlib`. Use `get_password_hash()` and `verify_password()` from `app/core/security.py`.

## API Endpoints

All endpoints are prefixed with `/api/v1`:

- **Auth:** `/auth/login`, `/auth/login-json`
- **Users:** `/users/` (CRUD + `/users/me` for current user + `/users/{id}/scopes`)
- **Roles:** `/roles/` (CRUD + `/roles/{id}/permissions` to assign permissions)
- **Permissions:** `/permissions/` (CRUD)
<!-- TEMPLATE:ORDERS:START -->
- **Orders:** `/orders/` (CRUD; reference model for data-scoped access via `require_scope`)
<!-- TEMPLATE:ORDERS:END -->

API documentation available at `http://localhost:8000/docs` when running.

## Important Notes

- The database has both native PostgreSQL functions (in `database/`) and SQLAlchemy models (in `backend/app/models/`). When adding features, consider which layer to modify.
- Some files have `_debug` suffixes - these are debugging versions and should not be used in production.
- `frontend/` is a React 19 + Vite + Tailwind v4 SPA (`npm run dev` / `npm run build`).
  Pages under `src/pages/`, API layer `src/lib/api/services.ts`, auth in `src/context/AuthContext.tsx`.
  The Roles page has a per-permission rule editor (effect + scope); Users has a `user_scopes`
  editor.
  <!-- TEMPLATE:ORDERS:START -->
  `src/pages/Orders.tsx` demonstrates data-scoped CRUD.
  <!-- TEMPLATE:ORDERS:END -->
- Always change default passwords and SECRET_KEY before deploying to production.
