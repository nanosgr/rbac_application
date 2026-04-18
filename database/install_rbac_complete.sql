-- =====================================
-- SCRIPT COMPLETO PARA RBAC_APP
-- Ejecutar este script conectado a la base de datos rbac_app
-- =====================================

-- Conectar a rbac_app:
-- psql -U rbac_user -d rbac_app

-- 1. CONFIGURACIÓN INICIAL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE SCHEMA IF NOT EXISTS rbac;
SET search_path TO rbac, public;
COMMENT ON SCHEMA rbac IS 'Esquema para el sistema de control de acceso basado en roles (RBAC)';

-- 2. CREAR TABLAS
CREATE TABLE rbac.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_email_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE TABLE rbac.roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE TABLE rbac.resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    resource_type VARCHAR(50) NOT NULL DEFAULT 'module',
    parent_id UUID,
    path VARCHAR(255),
    icon VARCHAR(50),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    FOREIGN KEY (parent_id) REFERENCES rbac.resources(id) ON DELETE CASCADE
);

CREATE TABLE rbac.permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    resource_id UUID NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    FOREIGN KEY (resource_id) REFERENCES rbac.resources(id) ON DELETE CASCADE,
    UNIQUE(name, action, resource_id)
);

CREATE TABLE rbac.user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    role_id UUID NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES rbac.users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES rbac.roles(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES rbac.users(id),
    UNIQUE(user_id, role_id)
);

CREATE TABLE rbac.role_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_id UUID NOT NULL,
    permission_id UUID NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    granted_by UUID,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (role_id) REFERENCES rbac.roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES rbac.permissions(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES rbac.users(id),
    UNIQUE(role_id, permission_id)
);

CREATE TABLE rbac.user_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    permission_id UUID NOT NULL,
    permission_type VARCHAR(10) NOT NULL CHECK (permission_type IN ('GRANT', 'DENY')),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    granted_by UUID,
    expires_at TIMESTAMP WITH TIME ZONE,
    reason TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES rbac.users(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES rbac.permissions(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES rbac.users(id),
    UNIQUE(user_id, permission_id, permission_type)
);

CREATE TABLE rbac.user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES rbac.users(id) ON DELETE CASCADE
);

CREATE TABLE rbac.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. FUNCIONES
CREATE OR REPLACE FUNCTION rbac.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON rbac.users
    FOR EACH ROW EXECUTE FUNCTION rbac.update_updated_at_column();
CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON rbac.roles
    FOR EACH ROW EXECUTE FUNCTION rbac.update_updated_at_column();
CREATE TRIGGER update_resources_updated_at BEFORE UPDATE ON rbac.resources
    FOR EACH ROW EXECUTE FUNCTION rbac.update_updated_at_column();
CREATE TRIGGER update_permissions_updated_at BEFORE UPDATE ON rbac.permissions
    FOR EACH ROW EXECUTE FUNCTION rbac.update_updated_at_column();

-- Función principal de verificación de permisos
CREATE OR REPLACE FUNCTION rbac.user_has_permission(
    p_user_id UUID,
    p_permission_name VARCHAR,
    p_action VARCHAR,
    p_resource_name VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    has_permission BOOLEAN := FALSE;
BEGIN
    SELECT EXISTS(
        SELECT 1
        FROM rbac.user_roles ur
        JOIN rbac.role_permissions rp ON ur.role_id = rp.role_id
        JOIN rbac.permissions p ON rp.permission_id = p.id
        JOIN rbac.resources r ON p.resource_id = r.id
        WHERE ur.user_id = p_user_id
        AND p.name = p_permission_name
        AND p.action = p_action
        AND r.name = p_resource_name
        AND ur.is_active = TRUE
        AND rp.is_active = TRUE
        AND p.is_active = TRUE
        AND r.is_active = TRUE
        AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
    ) INTO has_permission;
    
    RETURN has_permission;
END;
$$ LANGUAGE plpgsql;

-- 4. DATOS INICIALES
-- Insertar recursos
INSERT INTO rbac.resources (id, name, description, resource_type, path, icon, sort_order) VALUES
(uuid_generate_v4(), 'dashboard', 'Panel de control principal', 'module', '/dashboard', 'dashboard', 1),
(uuid_generate_v4(), 'users', 'Gestión de usuarios', 'module', '/users', 'users', 2),
(uuid_generate_v4(), 'roles', 'Gestión de roles', 'module', '/roles', 'shield', 3),
(uuid_generate_v4(), 'permissions', 'Gestión de permisos', 'module', '/permissions', 'key', 4),
(uuid_generate_v4(), 'audit', 'Auditoría del sistema', 'module', '/audit', 'file-text', 5),
(uuid_generate_v4(), 'settings', 'Configuración del sistema', 'module', '/settings', 'settings', 6);

-- Insertar roles
INSERT INTO rbac.roles (id, name, description, is_system_role) VALUES
(uuid_generate_v4(), 'Super Admin', 'Administrador con acceso total al sistema', true),
(uuid_generate_v4(), 'Admin', 'Administrador con permisos de gestión', true),
(uuid_generate_v4(), 'User Manager', 'Gestor de usuarios y roles', true),
(uuid_generate_v4(), 'Auditor', 'Usuario con acceso de solo lectura para auditoría', true),
(uuid_generate_v4(), 'User', 'Usuario básico del sistema', true);

-- Insertar permisos
INSERT INTO rbac.permissions (name, action, resource_id, description)
SELECT 'dashboard_view', 'read', id, 'Ver el panel de control' FROM rbac.resources WHERE name = 'dashboard'
UNION ALL
SELECT 'dashboard_stats', 'read', id, 'Ver estadísticas del dashboard' FROM rbac.resources WHERE name = 'dashboard'
UNION ALL
SELECT 'users_view', 'read', id, 'Ver lista de usuarios' FROM rbac.resources WHERE name = 'users'
UNION ALL
SELECT 'users_create', 'create', id, 'Crear nuevos usuarios' FROM rbac.resources WHERE name = 'users'
UNION ALL
SELECT 'users_edit', 'update', id, 'Editar usuarios existentes' FROM rbac.resources WHERE name = 'users'
UNION ALL
SELECT 'users_delete', 'delete', id, 'Eliminar usuarios' FROM rbac.resources WHERE name = 'users'
UNION ALL
SELECT 'roles_view', 'read', id, 'Ver lista de roles' FROM rbac.resources WHERE name = 'roles'
UNION ALL
SELECT 'roles_create', 'create', id, 'Crear nuevos roles' FROM rbac.resources WHERE name = 'roles'
UNION ALL
SELECT 'roles_edit', 'update', id, 'Editar roles existentes' FROM rbac.resources WHERE name = 'roles'
UNION ALL
SELECT 'roles_delete', 'delete', id, 'Eliminar roles' FROM rbac.resources WHERE name = 'roles'
UNION ALL
SELECT 'permissions_view', 'read', id, 'Ver lista de permisos' FROM rbac.resources WHERE name = 'permissions'
UNION ALL
SELECT 'permissions_create', 'create', id, 'Crear nuevos permisos' FROM rbac.resources WHERE name = 'permissions'
UNION ALL
SELECT 'permissions_edit', 'update', id, 'Editar permisos existentes' FROM rbac.resources WHERE name = 'permissions'
UNION ALL
SELECT 'permissions_delete', 'delete', id, 'Eliminar permisos' FROM rbac.resources WHERE name = 'permissions'
UNION ALL
SELECT 'audit_view', 'read', id, 'Ver logs de auditoría' FROM rbac.resources WHERE name = 'audit'
UNION ALL
SELECT 'audit_export', 'read', id, 'Exportar logs de auditoría' FROM rbac.resources WHERE name = 'audit'
UNION ALL
SELECT 'settings_view', 'read', id, 'Ver configuraciones del sistema' FROM rbac.resources WHERE name = 'settings'
UNION ALL
SELECT 'settings_edit', 'update', id, 'Modificar configuraciones del sistema' FROM rbac.resources WHERE name = 'settings';

-- Crear usuario admin
INSERT INTO rbac.users (id, username, email, password_hash, first_name, last_name, is_email_verified) VALUES
(uuid_generate_v4(), 'admin', 'admin@rbacapp.com', crypt('admin123', gen_salt('bf')), 'System', 'Administrator', true);

-- Asignar rol Super Admin al usuario admin
INSERT INTO rbac.user_roles (user_id, role_id, assigned_by)
SELECT u.id, r.id, u.id
FROM rbac.users u, rbac.roles r
WHERE u.username = 'admin' AND r.name = 'Super Admin';

-- Asignar todos los permisos al rol Super Admin
INSERT INTO rbac.role_permissions (role_id, permission_id, granted_by)
SELECT r.id, p.id, u.id
FROM rbac.roles r, rbac.permissions p, rbac.users u
WHERE r.name = 'Super Admin' AND u.username = 'admin';

-- 5. VISTA ÚTIL
CREATE VIEW rbac.user_roles_view AS
SELECT 
    u.id as user_id,
    u.username,
    u.email,
    u.first_name,
    u.last_name,
    u.is_active as user_active,
    r.id as role_id,
    r.name as role_name,
    r.description as role_description,
    ur.assigned_at,
    ur.expires_at,
    ur.is_active as assignment_active
FROM rbac.users u
LEFT JOIN rbac.user_roles ur ON u.id = ur.user_id
LEFT JOIN rbac.roles r ON ur.role_id = r.id
WHERE u.is_active = TRUE;

-- 6. VERIFICACIÓN FINAL
\echo '=== VERIFICACIÓN DE INSTALACIÓN ==='
SELECT 
    'users' as tabla, COUNT(*) as registros
FROM rbac.users
UNION ALL
SELECT 'roles', COUNT(*) FROM rbac.roles
UNION ALL
SELECT 'resources', COUNT(*) FROM rbac.resources
UNION ALL
SELECT 'permissions', COUNT(*) FROM rbac.permissions
UNION ALL
SELECT 'user_roles', COUNT(*) FROM rbac.user_roles
UNION ALL
SELECT 'role_permissions', COUNT(*) FROM rbac.role_permissions;

\echo '=== USUARIO ADMIN ==='
SELECT username, email, first_name, last_name, role_name
FROM rbac.user_roles_view 
WHERE username = 'admin';

\echo '=== PRUEBA DE PERMISOS ==='
SELECT rbac.user_has_permission(
    (SELECT id FROM rbac.users WHERE username = 'admin'),
    'dashboard_view',
    'read',
    'dashboard'
) as admin_puede_ver_dashboard;

\echo '=== TABLAS CREADAS ==='
\dt rbac.*

\echo '=== INSTALACIÓN COMPLETADA ==='
\echo 'Usuario: admin'
\echo 'Password: admin123'
\echo 'Email: admin@rbacapp.com'
