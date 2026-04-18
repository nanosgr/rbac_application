#!/usr/bin/env bash
# Abre una sesión psql dentro del contenedor de PostgreSQL
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Conectando a PostgreSQL (rbac_app)..."
docker compose exec postgres psql -U rbac_user -d rbac_app
