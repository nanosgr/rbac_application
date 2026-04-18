#!/bin/bash

# =====================================
# RBAC Application Database Setup Script v2
# PostgreSQL 17 - Mejorado para problemas de autenticación
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
POSTGRES_USER="postgres"

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

# Función para detectar el método de autenticación
detect_auth_method() {
    print_message "Detectando método de autenticación de PostgreSQL..."
    
    # Intentar conexión como usuario postgres sin contraseña (peer auth)
    if sudo -u postgres psql -c "SELECT 1;" >/dev/null 2>&1; then
        print_success "Usando autenticación peer (sin contraseña)"
        return 0
    else
        print_warning "Se requiere autenticación por contraseña"
        return 1
    fi
}

# Función para crear usuario y base de datos con peer auth
create_with_peer_auth() {
    print_message "Creando usuario y base de datos con autenticación peer..."
    
    # Crear usuario
    print_message "Creando usuario '$DB_USER'..."
    sudo -u postgres psql -c "
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='$DB_USER') THEN
                CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
                ALTER USER $DB_USER CREATEDB;
                RAISE NOTICE 'Usuario $DB_USER creado exitosamente';
            ELSE
                RAISE NOTICE 'Usuario $DB_USER ya existe';
            END IF;
        END
        \$\$;
    " 2>/dev/null
    
    if [ $? -eq 0 ]; then
        print_success "Usuario '$DB_USER' configurado exitosamente"
    else
        print_error "Error al configurar el usuario '$DB_USER'"
        return 1
    fi
    
    # Crear base de datos
    print_message "Creando base de datos '$DB_NAME'..."
    sudo -u postgres psql -c "
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='$DB_NAME') THEN
                CREATE DATABASE $DB_NAME OWNER $DB_USER;
                RAISE NOTICE 'Base de datos $DB_NAME creada exitosamente';
            ELSE
                RAISE NOTICE 'Base de datos $DB_NAME ya existe';
            END IF;
        END
        \$\$;
        GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
    " 2>/dev/null
    
    if [ $? -eq 0 ]; then
        print_success "Base de datos '$DB_NAME' configurada exitosamente"
        return 0
    else
        print_error "Error al crear la base de datos '$DB_NAME'"
        return 1
    fi
}

# Función para crear usuario y base de datos con contraseña
create_with_password_auth() {
    print_message "Configurando con autenticación por contraseña..."
    
    echo -n "Ingresa la contraseña del usuario postgres: "
    read -s POSTGRES_PASSWORD
    echo
    
    # Crear usuario
    print_message "Creando usuario '$DB_USER'..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d postgres -c "
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='$DB_USER') THEN
                CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
                ALTER USER $DB_USER CREATEDB;
                RAISE NOTICE 'Usuario $DB_USER creado exitosamente';
            ELSE
                RAISE NOTICE 'Usuario $DB_USER ya existe';
            END IF;
        END
        \$\$;
    " 2>/dev/null
    
    if [ $? -ne 0 ]; then
        print_error "Error al crear el usuario. Verifica la contraseña de postgres."
        return 1
    fi
    
    # Crear base de datos
    print_message "Creando base de datos '$DB_NAME'..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d postgres -c "
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='$DB_NAME') THEN
                CREATE DATABASE $DB_NAME OWNER $DB_USER;
                RAISE NOTICE 'Base de datos $DB_NAME creada exitosamente';
            ELSE
                RAISE NOTICE 'Base de datos $DB_NAME ya existe';
            END IF;
        END
        \$\$;
        GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
    " 2>/dev/null
    
    if [ $? -eq 0 ]; then
        print_success "Base de datos '$DB_NAME' configurada exitosamente"
        return 0
    else
        print_error "Error al crear la base de datos '$DB_NAME'"
        return 1
    fi
}

# Función para verificar conexión con la nueva base de datos
test_connection() {
    print_message "Verificando conexión a la nueva base de datos..."
    
    # Intentar conectar sin variable de entorno primero
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
        print_success "Conexión exitosa sin PGPASSWORD"
        return 0
    fi
    
    # Intentar con PGPASSWORD
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
        print_success "Conexión exitosa con PGPASSWORD"
        export PGPASSWORD="$DB_PASSWORD"
        return 0
    fi
    
    print_error "No se puede conectar a la base de datos '$DB_NAME'"
    return 1
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
    
    # Intentar ejecutar el script
    if [ -n "$PGPASSWORD" ]; then
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$script_file" -v ON_ERROR_STOP=1 >/dev/null 2>&1
    else
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$script_file" -v ON_ERROR_STOP=1 >/dev/null 2>&1
    fi
    
    if [ $? -eq 0 ]; then
        print_success "$description completado"
        return 0
    else
        print_error "Error en: $description"
        echo "Ejecuta manualmente para ver el error detallado:"
        echo "psql -U $DB_USER -d $DB_NAME -f $script_file"
        return 1
    fi
}

# Función para mostrar instrucciones manuales
show_manual_instructions() {
    echo ""
    print_warning "=== INSTRUCCIONES PARA CONFIGURACIÓN MANUAL ==="
    echo ""
    echo "Si el script automático falla, puedes configurar manualmente:"
    echo ""
    echo "1. Conectar como superusuario:"
    echo "   sudo -u postgres psql"
    echo ""
    echo "2. Crear usuario y base de datos:"
    echo "   CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    echo "   ALTER USER $DB_USER CREATEDB;"
    echo "   CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    echo "   GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    echo "   \\q"
    echo ""
    echo "3. Conectar a la nueva base de datos:"
    echo "   psql -U $DB_USER -d $DB_NAME"
    echo ""
    echo "4. Ejecutar scripts en orden:"
    echo "   \\i 01_create_database.sql"
    echo "   \\i 02_create_tables.sql"
    echo "   \\i 03_create_indexes.sql"
    echo "   \\i 04_functions_triggers.sql"
    echo "   \\i 05_initial_data.sql"
    echo "   \\i 06_views.sql"
    echo "   \\i 07_procedures.sql"
    echo ""
}

# Función principal
main() {
    echo "============================================="
    echo "   RBAC Application Database Setup v2"
    echo "============================================="
    echo ""
    
    # Verificaciones previas
    check_postgresql
    
    # Detectar método de autenticación y crear usuario/bd
    if detect_auth_method; then
        if ! create_with_peer_auth; then
            print_warning "Método peer falló, intentando con contraseña..."
            create_with_password_auth || {
                show_manual_instructions
                exit 1
            }
        fi
    else
        create_with_password_auth || {
            show_manual_instructions
            exit 1
        }
    fi
    
    # Verificar conexión a la nueva base de datos
    if ! test_connection; then
        show_manual_instructions
        exit 1
    fi
    
    # Ejecutar scripts SQL en orden
    echo ""
    print_message "Ejecutando scripts de configuración de base de datos..."
    echo ""
    
    execute_sql_script "01_create_database.sql" "Configurando extensiones y esquemas" || exit 1
    execute_sql_script "02_create_tables.sql" "Creando tablas" || exit 1
    execute_sql_script "03_create_indexes.sql" "Creando índices" || exit 1
    execute_sql_script "04_functions_triggers.sql" "Creando funciones y triggers" || exit 1
    execute_sql_script "05_initial_data.sql" "Insertando datos iniciales" || exit 1
    execute_sql_script "06_views.sql" "Creando vistas" || exit 1
    execute_sql_script "07_procedures.sql" "Creando procedimientos almacenados" || exit 1
    
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
    echo "Para probar la instalación:"
    echo "  psql -U $DB_USER -d $DB_NAME -f test_database.sql"
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
