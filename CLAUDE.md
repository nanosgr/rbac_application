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
- **app/core/** - Core functionality (config, security, dependencies)
- **app/models/** - SQLAlchemy ORM models
- **app/schemas/** - Pydantic schemas for validation
- **app/services/** - Business logic and CRUD operations
- **app/db/** - Database configuration and initialization

### RBAC Permission System

**Permission Format:** `resource:action` (e.g., `users:read`, `roles:create`)

**Permission Checking:**
1. Superusers bypass all permission checks
2. Regular users inherit permissions from their assigned roles
3. Use the `require_permissions()` dependency in endpoints to enforce permissions

**Example endpoint with permissions:**
```python
from app.core.deps import require_permissions

@router.get("/users")
def list_users(
    current_user: User = Depends(require_permissions(["users:read"]))
):
    # Only users with "users:read" permission can access
    pass
```

**Convenience functions:** Use `require_user_read()`, `require_role_create()`, etc. from `app/core/deps.py` for common permission checks.

### Database Schema

The system uses two levels of database abstraction:

1. **PostgreSQL Native (database/ folder):** Complete schema with triggers, stored procedures, and views in the `rbac` schema
2. **SQLAlchemy ORM (backend/app/models/):** Simplified models for the FastAPI application

**Key relationships:**
- Users ↔ Roles (many-to-many via user_roles)
- Roles ↔ Permissions (many-to-many via role_permissions)

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
- **Users:** `/users/` (CRUD + `/users/me` for current user)
- **Roles:** `/roles/` (CRUD + `/roles/{id}/permissions` to assign permissions)
- **Permissions:** `/permissions/` (CRUD)

API documentation available at `http://localhost:8000/docs` when running.

## Important Notes

- The database has both native PostgreSQL functions (in `database/`) and SQLAlchemy models (in `backend/app/models/`). When adding features, consider which layer to modify.
- Some files have `_debug` suffixes - these are debugging versions and should not be used in production.
- The frontend folder is empty and not yet implemented.
- Always change default passwords and SECRET_KEY before deploying to production.
