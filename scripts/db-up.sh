#!/usr/bin/env bash
# Levanta el contenedor de PostgreSQL
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Iniciando PostgreSQL..."
docker compose up -d postgres

echo ""
echo "Esperando a que PostgreSQL esté listo..."
until docker compose exec postgres pg_isready -U rbac_user -d rbac_app > /dev/null 2>&1; do
    printf "."
    sleep 1
done

echo ""
echo "PostgreSQL listo."
echo ""
echo "  Host:          localhost:5432"
echo "  Base de datos: rbac_app"
echo "  Usuario:       rbac_user"
echo "  Password:      rbac_password"
echo ""
echo "Para aplicar migraciones y datos semilla:"
echo "  ./scripts/db-migrate.sh"
