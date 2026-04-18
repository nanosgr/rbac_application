#!/bin/bash

# =====================================
# Script para Agregar Permisos a claude_user
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
echo "   Configuración de Permisos claude_user"
echo "============================================="

# Mostrar permisos actuales
print_message "Permisos actuales de claude_user:"
sudo -u postgres psql -c "
SELECT 
    rolname,
    CASE WHEN rolsuper THEN 'Superusuario' ELSE '' END ||
    CASE WHEN rolcreaterole THEN ', Crear rol' ELSE '' END ||
    CASE WHEN rolcreatedb THEN ', Crear BD' ELSE '' END ||
    CASE WHEN rolcanlogin THEN ', Login' ELSE '' END ||
    CASE WHEN rolreplication THEN ', Replicación' ELSE '' END as atributos
FROM pg_roles 
WHERE rolname = 'claude_user';
"

echo ""
print_message "¿Qué permisos quieres agregar a claude_user?"
echo ""
echo "1. Solo crear bases de datos (CREATEDB)"
echo "2. Crear roles y bases de datos (CREATEROLE + CREATEDB)"
echo "3. Permisos de superusuario (SUPERUSER - máximos permisos)"
echo "4. Ver opciones detalladas"
echo "5. Cancelar"
echo ""
read -p "Selecciona una opción (1-5): " choice

case $choice in
    1)
        print_message "Agregando permiso CREATEDB a claude_user..."
        sudo -u postgres psql -c "ALTER USER claude_user CREATEDB;"
        ;;
    2)
        print_message "Agregando permisos CREATEROLE y CREATEDB a claude_user..."
        sudo -u postgres psql -c "ALTER USER claude_user CREATEROLE CREATEDB;"
        ;;
    3)
        print_message "Agregando permisos de SUPERUSUARIO a claude_user..."
        echo "⚠️  ADVERTENCIA: Esto dará permisos máximos a claude_user"
        read -p "¿Estás seguro? (y/N): " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            sudo -u postgres psql -c "ALTER USER claude_user SUPERUSER;"
        else
            print_message "Operación cancelada"
            exit 0
        fi
        ;;
    4)
        echo ""
        echo "📚 OPCIONES DETALLADAS DE PERMISOS:"
        echo ""
        echo "CREATEDB      - Puede crear bases de datos"
        echo "CREATEROLE    - Puede crear y gestionar otros roles/usuarios"
        echo "SUPERUSER     - Acceso total al sistema (incluye todos los permisos)"
        echo "LOGIN         - Puede conectarse (ya lo tiene)"
        echo "REPLICATION   - Puede hacer replicación de BD"
        echo ""
        echo "🎯 RECOMENDACIONES:"
        echo ""
        echo "Para desarrollo local: CREATEDB es suficiente"
        echo "Para administración: CREATEROLE + CREATEDB"
        echo "Solo para casos especiales: SUPERUSER"
        echo ""
        echo "Ejecuta el script nuevamente para aplicar cambios."
        exit 0
        ;;
    5)
        print_message "Operación cancelada"
        exit 0
        ;;
    *)
        print_error "Opción inválida"
        exit 1
        ;;
esac

if [ $? -eq 0 ]; then
    print_success "Permisos actualizados exitosamente"
    echo ""
    print_message "Permisos actuales de claude_user:"
    sudo -u postgres psql -c "
    SELECT 
        rolname,
        CASE WHEN rolsuper THEN 'Superusuario' ELSE '' END ||
        CASE WHEN rolcreaterole THEN ', Crear rol' ELSE '' END ||
        CASE WHEN rolcreatedb THEN ', Crear BD' ELSE '' END ||
        CASE WHEN rolcanlogin THEN ', Login' ELSE '' END ||
        CASE WHEN rolreplication THEN ', Replicación' ELSE '' END as atributos
    FROM pg_roles 
    WHERE rolname = 'claude_user';
    "
else
    print_error "Error al actualizar permisos"
    exit 1
fi

echo ""
print_success "Configuración completada!"
