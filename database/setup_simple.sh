#!/bin/bash

# =====================================
# RBAC Application Database Setup - Método Simplificado
# PostgreSQL 17
# =====================================

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
DB_NAME="rbac_app"
DB_USER="rbac_user"
DB_PASSWORD="rbac_password"

print_message() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "============================================="
echo "   RBAC Setup - Método Simplificado"
echo "============================================="

# Método 1: Usando sudo -u postgres (más confiable)
print_message "Creando usuario y base de datos..."

sudo -u postgres psql << EOF
-- Crear usuario si no existe
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
        ALTER USER $DB_USER CREATEDB;
    END IF;
END
\$\$;

-- Crear base de datos si no existe
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS $DB_NAME;
CREATE DATABASE $DB_NAME OWNER $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

\q
EOF

if [ $? -eq 0 ]; then
    print_success "Usuario y base de datos creados exitosamente"
else
    print_error "Error al crear usuario y base de datos"
    exit 1
fi

# Ejecutar scripts SQL
print_message "Ejecutando scripts SQL..."

for script in 01_create_database.sql 02_create_tables.sql 03_create_indexes.sql 04_functions_triggers.sql 05_initial_data.sql 06_views.sql 07_procedures.sql; do
    if [ -f "$script" ]; then
        print_message "Ejecutando $script..."
        PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -d "$DB_NAME" -f "$script" -v ON_ERROR_STOP=1
        if [ $? -eq 0 ]; then
            print_success "$script completado"
        else
            print_error "Error en $script"
            exit 1
        fi
    else
        print_error "Archivo $script no encontrado"
        exit 1
    fi
done

echo ""
print_success "¡Configuración completada exitosamente!"
echo ""
echo "Detalles de conexión:"
echo "  Base de datos: $DB_NAME"
echo "  Usuario: $DB_USER"
echo "  Contraseña: $DB_PASSWORD"
echo ""
echo "Para conectar:"
echo "  psql -U $DB_USER -d $DB_NAME"
echo ""
echo "Para probar:"
echo "  PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -d $DB_NAME -f test_database.sql"
