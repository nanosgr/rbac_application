#!/bin/bash

# =====================================
# Instalación RBAC - Con Solución de Autenticación
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
echo "   Instalación RBAC con Fix de Autenticación"
echo "============================================="

# 1. Crear/verificar usuario y base de datos
print_message "1. Configurando usuario y base de datos..."
sudo -u postgres psql << 'EOF'
-- Crear usuario si no existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='rbac_user') THEN
        CREATE USER rbac_user WITH PASSWORD 'rbac_password';
        ALTER USER rbac_user CREATEDB;
        RAISE NOTICE 'Usuario rbac_user creado';
    ELSE
        RAISE NOTICE 'Usuario rbac_user ya existe';
    END IF;
END
$$;

-- Crear base de datos si no existe
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='rbac_app' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS rbac_app;
CREATE DATABASE rbac_app OWNER rbac_user;
GRANT ALL PRIVILEGES ON DATABASE rbac_app TO rbac_user;
EOF

if [ $? -eq 0 ]; then
    print_success "Usuario y base de datos configurados"
else
    print_error "Error en configuración inicial"
    exit 1
fi

# 2. Detectar método de conexión que funciona
print_message "2. Detectando método de conexión..."

CONNECTION_METHOD=""
CONNECTION_CMD=""

# Probar diferentes métodos
if PGPASSWORD=rbac_password psql -h localhost -U rbac_user -d rbac_app -c "SELECT 1;" >/dev/null 2>&1; then
    CONNECTION_METHOD="localhost"
    CONNECTION_CMD="PGPASSWORD=rbac_password psql -h localhost -U rbac_user -d rbac_app"
elif PGPASSWORD=rbac_password psql -h 127.0.0.1 -U rbac_user -d rbac_app -c "SELECT 1;" >/dev/null 2>&1; then
    CONNECTION_METHOD="tcp"
    CONNECTION_CMD="PGPASSWORD=rbac_password psql -h 127.0.0.1 -U rbac_user -d rbac_app"
elif PGPASSWORD=rbac_password psql -U rbac_user -d rbac_app -c "SELECT 1;" >/dev/null 2>&1; then
    CONNECTION_METHOD="local"
    CONNECTION_CMD="PGPASSWORD=rbac_password psql -U rbac_user -d rbac_app"
fi

if [ -n "$CONNECTION_METHOD" ]; then
    print_success "Método de conexión encontrado: $CONNECTION_METHOD"
else
    print_warning "No se encontró método de conexión. Configurando autenticación..."
    
    # Configurar pg_hba.conf para permitir conexiones MD5
    PG_VERSION=$(sudo -u postgres psql -t -c "SHOW server_version;" | cut -d. -f1 | tr -d ' ')
    HBA_FILE="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    
    if [ -f "$HBA_FILE" ]; then
        print_message "Configurando autenticación en $HBA_FILE"
        sudo cp "$HBA_FILE" "$HBA_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Agregar reglas para rbac_user
        if ! grep -q "rbac_app.*rbac_user" "$HBA_FILE"; then
            echo "# RBAC Application - Added by installer" | sudo tee -a "$HBA_FILE"
            echo "host    rbac_app        rbac_user       127.0.0.1/32            md5" | sudo tee -a "$HBA_FILE"
            echo "host    rbac_app        rbac_user       ::1/128                 md5" | sudo tee -a "$HBA_FILE"
        fi
        
        print_message "Reiniciando PostgreSQL..."
        sudo systemctl restart postgresql
        sleep 2
        
        # Probar nuevamente
        if PGPASSWORD=rbac_password psql -h 127.0.0.1 -U rbac_user -d rbac_app -c "SELECT 1;" >/dev/null 2>&1; then
            CONNECTION_METHOD="tcp"
            CONNECTION_CMD="PGPASSWORD=rbac_password psql -h 127.0.0.1 -U rbac_user -d rbac_app"
            print_success "Autenticación configurada exitosamente"
        else
            print_error "No se pudo configurar la autenticación automáticamente"
            echo ""
            echo "SOLUCIÓN MANUAL:"
            echo "1. Editar: sudo nano $HBA_FILE"
            echo "2. Agregar línea: host rbac_app rbac_user 127.0.0.1/32 md5"
            echo "3. Reiniciar: sudo systemctl restart postgresql"
            echo "4. Conectar: PGPASSWORD=rbac_password psql -h 127.0.0.1 -U rbac_user -d rbac_app"
            exit 1
        fi
    else
        print_error "No se encontró archivo pg_hba.conf"
        exit 1
    fi
fi

# 3. Ejecutar instalación del esquema RBAC
print_message "3. Instalando esquema RBAC..."

if [ -f "install_rbac_complete.sql" ]; then
    case $CONNECTION_METHOD in
        "localhost")
            PGPASSWORD=rbac_password psql -h localhost -U rbac_user -d rbac_app -f install_rbac_complete.sql
            ;;
        "tcp")
            PGPASSWORD=rbac_password psql -h 127.0.0.1 -U rbac_user -d rbac_app -f install_rbac_complete.sql
            ;;
        "local")
            PGPASSWORD=rbac_password psql -U rbac_user -d rbac_app -f install_rbac_complete.sql
            ;;
    esac
    
    if [ $? -eq 0 ]; then
        print_success "¡Instalación RBAC completada exitosamente!"
        echo ""
        echo "📋 INFORMACIÓN DE CONEXIÓN:"
        echo "Comando de conexión: $CONNECTION_CMD"
        echo ""
        echo "📋 CREDENCIALES:"
        echo "Base de datos: rbac_app"
        echo "Usuario BD: rbac_user"
        echo "Password BD: rbac_password"
        echo ""
        echo "Usuario Admin App: admin"
        echo "Password Admin App: admin123"
        echo "Email: admin@rbacapp.com"
        echo ""
        echo "🔍 VERIFICAR INSTALACIÓN:"
        echo "$CONNECTION_CMD"
        echo "\\dt rbac.*"
        echo "SELECT * FROM rbac.users;"
    else
        print_error "Error en la instalación del esquema"
        exit 1
    fi
else
    print_error "Archivo install_rbac_complete.sql no encontrado"
    exit 1
fi

# 4. Crear script de conexión rápida
cat > connect_rbac.sh << EOF
#!/bin/bash
# Script de conexión rápida a RBAC
echo "Conectando a base de datos RBAC..."
$CONNECTION_CMD
EOF

chmod +x connect_rbac.sh
print_success "Script de conexión creado: ./connect_rbac.sh"

echo ""
print_success "🎉 ¡INSTALACIÓN COMPLETADA!"
