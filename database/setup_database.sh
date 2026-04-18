#!/bin/bash

# =====================================
# RBAC Application Database Setup Script
# PostgreSQL 17
# =====================================

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración de la base de datos
DB_NAME="rbac_app"
DB_USER="rbac_user"
DB_PASSWORD="rbac_password"
DB_HOST="localhost"
DB_PORT="5432"

# Función para imprimir mensajes
print_message() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Función para verificar si PostgreSQL está ejecutándose
check_postgresql() {
    print_message "Verificando si PostgreSQL está ejecutándose..."
    if ! systemctl is-active --quiet postgresql; then
        print_error "PostgreSQL no está ejecutándose. Por favor, inicia el servicio:"
        echo "sudo systemctl start postgresql"
        exit 1
    fi
    print_success "PostgreSQL está ejecutándose"
}

# Función para verificar conexión a PostgreSQL
check_connection() {
    print_message "Verificando conexión a PostgreSQL..."
    if ! psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
        print_error "No se puede conectar a PostgreSQL. Verifica que:"
        echo "  - PostgreSQL esté ejecutándose"
        echo "  - El usuario postgres exista y tenga permisos"
        echo "  - pg_hba.conf permita conexiones locales"
        exit 1
    fi
    print_success "Conexión a PostgreSQL exitosa"
}

# Función para crear usuario de base de datos
create_db_user() {
    print_message "Creando usuario de base de datos '$DB_USER'..."
    
    # Verificar si el usuario ya existe
    if psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -d postgres -t -c "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';" | grep -q 1; then
        print_warning "El usuario '$DB_USER' ya existe"
    else
        psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -d postgres -c "
            CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
            ALTER USER $DB_USER CREATEDB;
        " > /dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            print_success "Usuario '$DB_USER' creado exitosamente"
        else
            print_error "Error al crear el usuario '$DB_USER'"
            exit 1
        fi
    fi
}

# Función para crear base de datos
create_database() {
    print_message "Creando base de datos '$DB_NAME'..."
    
    # Verificar si la base de datos ya existe
    if psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';" | grep -q 1; then
        print_warning "La base de datos '$DB_NAME' ya existe"
        read -p "¿Deseas recrearla? (y/N): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_message "Eliminando base de datos existente..."
            psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" > /dev/null 2>&1
        else
            print_message "Continuando con la base de datos existente..."
            return 0
        fi
    fi
    
    psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -d postgres -c "
        CREATE DATABASE $DB_NAME OWNER $DB_USER;
        GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
    " > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        print_success "Base de datos '$DB_NAME' creada exitosamente"
    else
        print_error "Error al crear la base de datos '$DB_NAME'"
        exit 1
    fi
}

# Función para ejecutar script SQL
execute_sql_script() {
    local script_file=$1
    local description=$2
    
    if [ ! -f "$script_file" ]; then
        print_error "Archivo no encontrado: $script_file"
        return 1
    fi
    
    print_message "$description"
    
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$script_file" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        print_success "$description completado"
        return 0
    else
        print_error "Error en: $description"
        echo "Revisa el archivo: $script_file"
        return 1
    fi
}

# Función principal
main() {
    echo "============================================="
    echo "   RBAC Application Database Setup"
    echo "============================================="
    echo ""
    
    # Verificaciones previas
    check_postgresql
    check_connection
    
    # Crear usuario y base de datos
    create_db_user
    create_database
    
    # Ejecutar scripts SQL en orden
    echo ""
    print_message "Ejecutando scripts de configuración de base de datos..."
    echo ""
    
    execute_sql_script "01_create_database.sql" "Configurando extensiones y esquemas"
    execute_sql_script "02_create_tables.sql" "Creando tablas"
    execute_sql_script "03_create_indexes.sql" "Creando índices"
    execute_sql_script "04_functions_triggers.sql" "Creando funciones y triggers"
    execute_sql_script "05_initial_data.sql" "Insertando datos iniciales"
    execute_sql_script "06_views.sql" "Creando vistas"
    execute_sql_script "07_procedures.sql" "Creando procedimientos almacenados"
    
    echo ""
    print_success "¡Configuración de base de datos completada exitosamente!"
    echo ""
    echo "Detalles de conexión:"
    echo "  Host: $DB_HOST"
    echo "  Puerto: $DB_PORT"
    echo "  Base de datos: $DB_NAME"
    echo "  Usuario: $DB_USER"
    echo "  Contraseña: $DB_PASSWORD"
    echo ""
    echo "Usuario administrador por defecto:"
    echo "  Username: admin"
    echo "  Password: admin123"
    echo "  Email: admin@rbacapp.com"
    echo ""
    print_warning "IMPORTANTE: Cambia la contraseña del administrador después del primer login"
}

# Ejecutar función principal
main "$@"
