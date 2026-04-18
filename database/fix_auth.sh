#!/bin/bash

# =====================================
# Diagnóstico y Solución de Autenticación PostgreSQL
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
echo "   Diagnóstico Autenticación PostgreSQL"
echo "============================================="

# 1. Verificar usuario rbac_user
print_message "1. Verificando usuario rbac_user en PostgreSQL..."
sudo -u postgres psql -c "SELECT rolname, rolcanlogin FROM pg_roles WHERE rolname = 'rbac_user';"

# 2. Verificar base de datos rbac_app
print_message "2. Verificando base de datos rbac_app..."
sudo -u postgres psql -c "SELECT datname FROM pg_database WHERE datname = 'rbac_app';"

# 3. Intentar diferentes métodos de conexión
print_message "3. Probando métodos de conexión..."

echo "Método 1: Conexión local con contraseña explícita..."
if PGPASSWORD=rbac_password psql -h localhost -U rbac_user -d rbac_app -c "SELECT current_user;" 2>/dev/null; then
    print_success "✓ Método 1 FUNCIONA: -h localhost con PGPASSWORD"
    WORKING_METHOD="localhost"
else
    print_warning "✗ Método 1 falló"
fi

echo "Método 2: Conexión TCP/IP..."
if PGPASSWORD=rbac_password psql -h 127.0.0.1 -U rbac_user -d rbac_app -c "SELECT current_user;" 2>/dev/null; then
    print_success "✓ Método 2 FUNCIONA: -h 127.0.0.1 con PGPASSWORD"
    WORKING_METHOD="tcp"
else
    print_warning "✗ Método 2 falló"
fi

echo "Método 3: Conexión local sin host..."
if PGPASSWORD=rbac_password psql -U rbac_user -d rbac_app -c "SELECT current_user;" 2>/dev/null; then
    print_success "✓ Método 3 FUNCIONA: conexión local con PGPASSWORD"
    WORKING_METHOD="local"
else
    print_warning "✗ Método 3 falló"
fi

# 4. Verificar configuración pg_hba.conf
print_message "4. Analizando configuración de autenticación..."
PG_VERSION=$(sudo -u postgres psql -t -c "SHOW server_version;" | cut -d. -f1 | tr -d ' ')
HBA_FILE="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"

if [ -f "$HBA_FILE" ]; then
    print_message "Archivo pg_hba.conf encontrado: $HBA_FILE"
    echo "Configuraciones relevantes:"
    echo "=========================="
    grep -E "^(local|host)" "$HBA_FILE" | grep -v "^#"
    echo "=========================="
else
    print_warning "No se encontró pg_hba.conf en ubicación estándar"
    print_message "Buscando archivo..."
    sudo find /etc -name "pg_hba.conf" 2>/dev/null
fi

# 5. Mostrar soluciones
echo ""
print_message "5. SOLUCIONES DISPONIBLES:"
echo ""

if [ -n "$WORKING_METHOD" ]; then
    print_success "¡Hay un método que funciona!"
    case $WORKING_METHOD in
        "localhost")
            echo "Usa: PGPASSWORD=rbac_password psql -h localhost -U rbac_user -d rbac_app"
            ;;
        "tcp")
            echo "Usa: PGPASSWORD=rbac_password psql -h 127.0.0.1 -U rbac_user -d rbac_app"
            ;;
        "local")
            echo "Usa: PGPASSWORD=rbac_password psql -U rbac_user -d rbac_app"
            ;;
    esac
else
    print_warning "Ningún método funcionó. Necesitamos configurar la autenticación."
    echo ""
    echo "OPCIÓN A: Configurar autenticación MD5/SCRAM"
    echo "1. Editar pg_hba.conf:"
    echo "   sudo nano $HBA_FILE"
    echo "2. Cambiar la línea:"
    echo "   local   all             all                                     peer"
    echo "   Por:"
    echo "   local   all             all                                     md5"
    echo "3. Reiniciar PostgreSQL:"
    echo "   sudo systemctl restart postgresql"
    echo ""
    echo "OPCIÓN B: Usar conexión TCP/IP"
    echo "1. Agregar línea en pg_hba.conf:"
    echo "   host    all             all             127.0.0.1/32            md5"
    echo "2. Reiniciar PostgreSQL"
    echo "3. Usar: psql -h 127.0.0.1 -U rbac_user -d rbac_app"
    echo ""
    echo "OPCIÓN C: Crear usuario del sistema (más complejo)"
    echo "   sudo adduser rbac_user"
fi

echo ""
print_message "6. SCRIPT DE REPARACIÓN AUTOMÁTICA"
echo ""
read -p "¿Quieres que intente reparar la configuración automáticamente? (y/N): " -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_message "Creando backup de pg_hba.conf..."
    sudo cp "$HBA_FILE" "$HBA_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    
    print_message "Agregando configuración para rbac_user..."
    echo "# Configuración para RBAC" | sudo tee -a "$HBA_FILE"
    echo "host    rbac_app        rbac_user       127.0.0.1/32            md5" | sudo tee -a "$HBA_FILE"
    echo "host    rbac_app        rbac_user       ::1/128                 md5" | sudo tee -a "$HBA_FILE"
    
    print_message "Reiniciando PostgreSQL..."
    sudo systemctl restart postgresql
    
    print_message "Probando conexión reparada..."
    if PGPASSWORD=rbac_password psql -h 127.0.0.1 -U rbac_user -d rbac_app -c "SELECT 'Conexión exitosa!' as resultado;" 2>/dev/null; then
        print_success "¡REPARACIÓN EXITOSA!"
        echo ""
        echo "Ahora puedes conectar con:"
        echo "PGPASSWORD=rbac_password psql -h 127.0.0.1 -U rbac_user -d rbac_app"
    else
        print_error "La reparación no funcionó. Usar método manual."
    fi
fi

echo ""
print_message "Diagnóstico completado."
