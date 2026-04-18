#!/bin/bash

# =====================================
# Instalación RBAC - Método Directo
# =====================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "============================================="
echo "   Instalación Directa RBAC en rbac_app"
echo "============================================="

# Verificar si la base de datos existe
print_message "Verificando base de datos rbac_app..."
if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw rbac_app; then
    print_message "Creando base de datos rbac_app..."
    sudo -u postgres psql -c "
        CREATE USER rbac_user WITH PASSWORD 'rbac_password';
        ALTER USER rbac_user CREATEDB;
        CREATE DATABASE rbac_app OWNER rbac_user;
        GRANT ALL PRIVILEGES ON DATABASE rbac_app TO rbac_user;
    "
    if [ $? -eq 0 ]; then
        print_success "Base de datos rbac_app creada"
    else
        print_error "Error al crear la base de datos"
        exit 1
    fi
else
    print_message "Base de datos rbac_app ya existe"
fi

# Ejecutar el script completo
print_message "Ejecutando script completo de instalación..."
if [ -f "install_rbac_complete.sql" ]; then
    PGPASSWORD=rbac_password psql -U rbac_user -d rbac_app -f install_rbac_complete.sql
    if [ $? -eq 0 ]; then
        print_success "¡Instalación RBAC completada exitosamente!"
        echo ""
        echo "Para conectarte:"
        echo "  PGPASSWORD=rbac_password psql -U rbac_user -d rbac_app"
        echo ""
        echo "Para ver las tablas:"
        echo "  \\dt rbac.*"
        echo ""
        echo "Credenciales admin:"
        echo "  Username: admin"
        echo "  Password: admin123"
        echo "  Email: admin@rbacapp.com"
    else
        print_error "Error en la instalación"
        exit 1
    fi
else
    print_error "Archivo install_rbac_complete.sql no encontrado"
    exit 1
fi
