#!/bin/bash

# =====================================
# Script de Diagnóstico y Reparación PostgreSQL
# =====================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "============================================="
echo "   Diagnóstico PostgreSQL RBAC"
echo "============================================="

# 1. Verificar estado de PostgreSQL
print_message "1. Verificando estado de PostgreSQL..."
if systemctl is-active --quiet postgresql; then
    print_success "PostgreSQL está ejecutándose"
    systemctl status postgresql --no-pager -l
else
    print_error "PostgreSQL no está ejecutándose"
    echo "Para iniciarlo: sudo systemctl start postgresql"
    exit 1
fi

echo ""

# 2. Verificar versión
print_message "2. Verificando versión de PostgreSQL..."
sudo -u postgres psql -c "SELECT version();" 2>/dev/null || {
    print_error "No se puede conectar a PostgreSQL"
    exit 1
}

echo ""

# 3. Verificar usuarios existentes
print_message "3. Verificando usuarios existentes..."
sudo -u postgres psql -c "SELECT rolname, rolcreatedb, rolcanlogin FROM pg_roles WHERE rolname IN ('postgres', 'rbac_user');" 2>/dev/null

echo ""

# 4. Verificar bases de datos existentes
print_message "4. Verificando bases de datos existentes..."
sudo -u postgres psql -c "SELECT datname, datowner, datacl FROM pg_database WHERE datname IN ('postgres', 'rbac_app');" 2>/dev/null

echo ""

# 5. Verificar configuración de autenticación
print_message "5. Verificando configuración de autenticación..."
PG_VERSION=$(sudo -u postgres psql -t -c "SHOW server_version;" | cut -d. -f1 | tr -d ' ')
HBA_FILE="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"

if [ -f "$HBA_FILE" ]; then
    print_success "Archivo pg_hba.conf encontrado: $HBA_FILE"
    echo "Configuraciones locales relevantes:"
    grep -v "^#" "$HBA_FILE" | grep -v "^$" | grep -E "(local|127.0.0.1)"
else
    print_warning "No se encontró pg_hba.conf en la ubicación esperada"
    echo "Buscar con: sudo find /etc -name pg_hba.conf 2>/dev/null"
fi

echo ""

# 6. Intentar diferentes métodos de conexión
print_message "6. Probando métodos de conexión..."

echo "Método 1: Conexión peer como postgres..."
if sudo -u postgres psql -c "SELECT 'Conexión peer exitosa';" >/dev/null 2>&1; then
    print_success "✓ Conexión peer funciona"
else
    print_error "✗ Conexión peer falló"
fi

echo "Método 2: Conexión local como postgres..."
if psql -U postgres -d postgres -h localhost -c "SELECT 'Conexión local exitosa';" >/dev/null 2>&1; then
    print_success "✓ Conexión local sin contraseña funciona"
else
    print_warning "✗ Conexión local requiere contraseña"
fi

echo ""

# 7. Verificar si rbac_app existe
print_message "7. Verificando estado de rbac_app..."
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw rbac_app; then
    print_warning "Base de datos rbac_app YA EXISTE"
    echo "¿Quieres eliminarla y recrearla? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        sudo -u postgres psql -c "DROP DATABASE IF EXISTS rbac_app;"
        sudo -u postgres psql -c "DROP USER IF EXISTS rbac_user;"
        print_success "Base de datos y usuario eliminados"
    fi
else
    print_message "Base de datos rbac_app no existe (correcto para nueva instalación)"
fi

echo ""

# 8. Recomendaciones
print_message "8. Recomendaciones para la instalación:"
echo ""
echo "Opción A - Método más simple (recomendado):"
echo "  chmod +x setup_simple.sh"
echo "  ./setup_simple.sh"
echo ""
echo "Opción B - Si tienes problemas de permisos:"
echo "  sudo -u postgres createuser -d rbac_user"
echo "  sudo -u postgres psql -c \"ALTER USER rbac_user PASSWORD 'rbac_password';\""
echo "  sudo -u postgres createdb -O rbac_user rbac_app"
echo "  PGPASSWORD=rbac_password psql -U rbac_user -d rbac_app -f 01_create_database.sql"
echo ""
echo "Opción C - Configuración manual completa:"
echo "  sudo -u postgres psql"
echo "  CREATE USER rbac_user WITH PASSWORD 'rbac_password';"
echo "  ALTER USER rbac_user CREATEDB;"
echo "  CREATE DATABASE rbac_app OWNER rbac_user;"
echo "  \\q"
echo ""

# 9. Verificar archivos SQL
print_message "9. Verificando archivos SQL necesarios..."
required_files=("01_create_database.sql" "02_create_tables.sql" "03_create_indexes.sql" "04_functions_triggers.sql" "05_initial_data.sql" "06_views.sql" "07_procedures.sql")

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_success "✓ $file"
    else
        print_error "✗ $file FALTANTE"
    fi
done

echo ""
print_message "Diagnóstico completado."
