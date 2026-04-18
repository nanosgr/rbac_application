# RBAC Application Database

Esta carpeta contiene todos los scripts necesarios para configurar la base de datos PostgreSQL 17 para la aplicación RBAC (Role-Based Access Control).

## Estructura de Archivos

### Scripts SQL (ejecutar en orden)
1. **01_create_database.sql** - Configuración inicial, extensiones y esquemas
2. **02_create_tables.sql** - Creación de todas las tablas del sistema
3. **03_create_indexes.sql** - Índices para optimización de consultas
4. **04_functions_triggers.sql** - Funciones y triggers para lógica de negocio
5. **05_initial_data.sql** - Datos iniciales del sistema (roles, permisos, usuario admin)
6. **06_views.sql** - Vistas para facilitar consultas complejas
7. **07_procedures.sql** - Procedimientos almacenados para operaciones comunes

### Scripts de Automatización
- **setup_database.sh** - Script bash para configuración automática completa
- **README.md** - Este archivo de documentación

## Configuración Rápida

### Opción 1: Automatizada (Recomendada)
```bash
# Dar permisos de ejecución al script
chmod +x setup_database.sh

# Ejecutar configuración automática
./setup_database.sh
```

### Opción 2: Manual
```bash
# Conectar como superusuario de PostgreSQL
sudo -u postgres psql

# Crear usuario y base de datos
CREATE USER rbac_user WITH PASSWORD 'rbac_password';
CREATE DATABASE rbac_app OWNER rbac_user;
GRANT ALL PRIVILEGES ON DATABASE rbac_app TO rbac_user;

# Salir y conectar a la nueva base de datos
\q
psql -U rbac_user -d rbac_app

# Ejecutar scripts en orden
\i 01_create_database.sql
\i 02_create_tables.sql
\i 03_create_indexes.sql
\i 04_functions_triggers.sql
\i 05_initial_data.sql
\i 06_views.sql
\i 07_procedures.sql
```

## Configuración de Conexión

### Parámetros por defecto:
- **Host:** localhost
- **Puerto:** 5432
- **Base de datos:** rbac_app
- **Usuario:** rbac_user
- **Contraseña:** rbac_password

### Usuario administrador inicial:
- **Username:** admin
- **Password:** admin123
- **Email:** admin@rbacapp.com

> ⚠️ **IMPORTANTE:** Cambia la contraseña del administrador después del primer login

## Arquitectura de la Base de Datos

### Tablas Principales

#### Gestión de Usuarios
- **users** - Información de usuarios del sistema
- **user_sessions** - Sesiones activas de usuarios

#### Sistema RBAC
- **roles** - Roles del sistema
- **resources** - Recursos/módulos protegidos
- **permissions** - Permisos específicos sobre recursos
- **user_roles** - Asignación de roles a usuarios
- **role_permissions** - Permisos asignados a roles
- **user_permissions** - Permisos directos a usuarios (excepciones)

#### Auditoría
- **audit_log** - Registro de todas las acciones del sistema

### Funciones Importantes

#### Verificación de Permisos
```sql
-- Verificar si un usuario tiene un permiso específico
SELECT user_has_permission(
    'user_id_uuid',
    'permission_name',
    'action',
    'resource_name'
);

-- Obtener todos los permisos de un usuario
SELECT * FROM get_user_permissions('user_id_uuid');
```

#### Gestión de Usuarios
```sql
-- Crear usuario con rol
SELECT create_user_with_role(
    'username',
    'email@example.com',
    'password',
    'First Name',
    'Last Name',
    'Role Name',
    'created_by_user_id'
);

-- Cambiar contraseña
SELECT change_user_password(
    'user_id_uuid',
    'old_password',
    'new_password'
);
```

### Vistas Útiles

- **user_roles_view** - Usuarios con sus roles asignados
- **role_permissions_view** - Roles con sus permisos
- **user_effective_permissions** - Todos los permisos efectivos por usuario
- **resources_hierarchy** - Estructura jerárquica de recursos
- **active_user_sessions** - Sesiones activas
- **system_stats** - Estadísticas del sistema

## Mantenimiento

### Limpiar sesiones expiradas
```sql
SELECT clean_expired_sessions();
```

### Consultar estadísticas del sistema
```sql
SELECT * FROM system_stats;
```

### Ver auditoría reciente
```sql
SELECT * FROM audit_log_detailed 
WHERE timestamp >= CURRENT_DATE 
ORDER BY timestamp DESC;
```

## Seguridad

- Las contraseñas se almacenan usando bcrypt
- Auditoría automática de todas las operaciones importantes
- Sesiones con tokens seguros y expiración automática
- Bloqueo de cuentas por intentos fallidos de login
- Permisos granulares a nivel de recurso y acción

## Roles del Sistema

### Roles Predefinidos:

1. **Super Admin** - Acceso total al sistema
2. **Admin** - Administrador con permisos de gestión
3. **User Manager** - Gestor de usuarios y roles
4. **Auditor** - Acceso de solo lectura para auditoría
5. **User** - Usuario básico del sistema

## Recursos del Sistema

### Módulos Principales:

- **dashboard** - Panel de control principal
- **users** - Gestión de usuarios
- **roles** - Gestión de roles
- **permissions** - Gestión de permisos
- **audit** - Auditoría del sistema
- **settings** - Configuración del sistema

### Acciones Disponibles:

- **read** - Ver/consultar información
- **create** - Crear nuevos elementos
- **update** - Modificar elementos existentes
- **delete** - Eliminar elementos

## Troubleshooting

### Problemas Comunes

#### Error de conexión a PostgreSQL
```bash
# Verificar que PostgreSQL esté ejecutándose
sudo systemctl status postgresql

# Iniciar PostgreSQL si no está activo
sudo systemctl start postgresql

# Verificar configuración de pg_hba.conf
sudo nano /etc/postgresql/17/main/pg_hba.conf
```

#### Error de permisos
```bash
# Asegurar que el usuario tenga permisos
sudo -u postgres psql
GRANT ALL PRIVILEGES ON DATABASE rbac_app TO rbac_user;
```

#### Reiniciar configuración
```bash
# Eliminar y recrear la base de datos
sudo -u postgres psql
DROP DATABASE IF EXISTS rbac_app;
DROP USER IF EXISTS rbac_user;

# Ejecutar setup nuevamente
./setup_database.sh
```

## Testing

### Verificar instalación
```sql
-- Conectar a la base de datos
psql -U rbac_user -d rbac_app

-- Verificar tablas creadas
\dt rbac.*

-- Verificar datos iniciales
SELECT username FROM rbac.users;
SELECT name FROM rbac.roles;
SELECT name FROM rbac.resources;

-- Probar función de permisos
SELECT rbac.user_has_permission(
    (SELECT id FROM rbac.users WHERE username = 'admin'),
    'dashboard_view',
    'read', 
    'dashboard'
);
```

## Backup y Restore

### Crear backup
```bash
pg_dump -U rbac_user -h localhost rbac_app > rbac_backup.sql
```

### Restaurar backup
```bash
psql -U rbac_user -h localhost rbac_app < rbac_backup.sql
```

## Contribución

Para modificar la estructura de la base de datos:

1. Crear un nuevo script numerado (ej: 08_new_feature.sql)
2. Actualizar el script setup_database.sh para incluir el nuevo archivo
3. Documentar los cambios en este README
4. Probar la configuración completa desde cero

## Licencia

Este proyecto está bajo licencia MIT.
