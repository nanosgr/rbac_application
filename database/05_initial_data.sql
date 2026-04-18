-- =====================================
-- RBAC Initial Data
-- =====================================

SET search_path TO rbac, public;

-- Insertar recursos base del sistema
INSERT INTO resources (id, name, description, resource_type, path, icon, sort_order) VALUES
-- Módulos principales
(uuid_generate_v4(), 'dashboard', 'Panel de control principal', 'module', '/dashboard', 'dashboard', 1),
(uuid_generate_v4(), 'users', 'Gestión de usuarios', 'module', '/users', 'users', 2),
(uuid_generate_v4(), 'roles', 'Gestión de roles', 'module', '/roles', 'shield', 3),
(uuid_generate_v4(), 'permissions', 'Gestión de permisos', 'module', '/permissions', 'key', 4),
(uuid_generate_v4(), 'audit', 'Auditoría del sistema', 'module', '/audit', 'file-text', 5),
(uuid_generate_v4(), 'settings', 'Configuración del sistema', 'module', '/settings', 'settings', 6);

-- Obtener IDs de los recursos para crear permisos
DO $$
DECLARE
    dashboard_id UUID;
    users_id UUID;
    roles_id UUID;
    permissions_id UUID;
    audit_id UUID;
    settings_id UUID;
BEGIN
    -- Obtener IDs de recursos
    SELECT id INTO dashboard_id FROM resources WHERE name = 'dashboard';
    SELECT id INTO users_id FROM resources WHERE name = 'users';
    SELECT id INTO roles_id FROM resources WHERE name = 'roles';  
    SELECT id INTO permissions_id FROM resources WHERE name = 'permissions';
    SELECT id INTO audit_id FROM resources WHERE name = 'audit';
    SELECT id INTO settings_id FROM resources WHERE name = 'settings';

    -- Insertar permisos para Dashboard
    INSERT INTO permissions (name, action, resource_id, description) VALUES
    ('dashboard_view', 'read', dashboard_id, 'Ver el panel de control'),
    ('dashboard_stats', 'read', dashboard_id, 'Ver estadísticas del dashboard');

    -- Insertar permisos para Users
    INSERT INTO permissions (name, action, resource_id, description) VALUES
    ('users_view', 'read', users_id, 'Ver lista de usuarios'),
    ('users_create', 'create', users_id, 'Crear nuevos usuarios'),
    ('users_edit', 'update', users_id, 'Editar usuarios existentes'),
    ('users_delete', 'delete', users_id, 'Eliminar usuarios'),
    ('users_assign_roles', 'update', users_id, 'Asignar roles a usuarios'),
    ('users_manage_permissions', 'update', users_id, 'Gestionar permisos directos de usuarios');

    -- Insertar permisos para Roles
    INSERT INTO permissions (name, action, resource_id, description) VALUES
    ('roles_view', 'read', roles_id, 'Ver lista de roles'),
    ('roles_create', 'create', roles_id, 'Crear nuevos roles'),
    ('roles_edit', 'update', roles_id, 'Editar roles existentes'),
    ('roles_delete', 'delete', roles_id, 'Eliminar roles'),
    ('roles_assign_permissions', 'update', roles_id, 'Asignar permisos a roles');

    -- Insertar permisos para Permissions
    INSERT INTO permissions (name, action, resource_id, description) VALUES
    ('permissions_view', 'read', permissions_id, 'Ver lista de permisos'),
    ('permissions_create', 'create', permissions_id, 'Crear nuevos permisos'),
    ('permissions_edit', 'update', permissions_id, 'Editar permisos existentes'),
    ('permissions_delete', 'delete', permissions_id, 'Eliminar permisos');

    -- Insertar permisos para Audit
    INSERT INTO permissions (name, action, resource_id, description) VALUES
    ('audit_view', 'read', audit_id, 'Ver logs de auditoría'),
    ('audit_export', 'read', audit_id, 'Exportar logs de auditoría');

    -- Insertar permisos para Settings
    INSERT INTO permissions (name, action, resource_id, description) VALUES
    ('settings_view', 'read', settings_id, 'Ver configuraciones del sistema'),
    ('settings_edit', 'update', settings_id, 'Modificar configuraciones del sistema');
END $$;

-- Insertar roles del sistema
INSERT INTO roles (id, name, description, is_system_role) VALUES
(uuid_generate_v4(), 'Super Admin', 'Administrador con acceso total al sistema', true),
(uuid_generate_v4(), 'Admin', 'Administrador con permisos de gestión', true),
(uuid_generate_v4(), 'User Manager', 'Gestor de usuarios y roles', true),
(uuid_generate_v4(), 'Auditor', 'Usuario con acceso de solo lectura para auditoría', true),
(uuid_generate_v4(), 'User', 'Usuario básico del sistema', true);

-- Crear usuario administrador por defecto
INSERT INTO users (id, username, email, password_hash, first_name, last_name, is_email_verified) VALUES
(uuid_generate_v4(), 'admin', 'admin@rbacapp.com', crypt('admin123', gen_salt('bf')), 'System', 'Administrator', true);

-- Asignar rol Super Admin al usuario administrador
DO $$
DECLARE
    admin_user_id UUID;
    super_admin_role_id UUID;
BEGIN
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin';
    SELECT id INTO super_admin_role_id FROM roles WHERE name = 'Super Admin';
    
    INSERT INTO user_roles (user_id, role_id, assigned_by) VALUES
    (admin_user_id, super_admin_role_id, admin_user_id);
END $$;

-- Asignar todos los permisos al rol Super Admin
DO $$
DECLARE
    super_admin_role_id UUID;
    admin_user_id UUID;
    perm_record RECORD;
BEGIN
    SELECT id INTO super_admin_role_id FROM roles WHERE name = 'Super Admin';
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin';
    
    FOR perm_record IN SELECT id FROM permissions LOOP
        INSERT INTO role_permissions (role_id, permission_id, granted_by) VALUES
        (super_admin_role_id, perm_record.id, admin_user_id);
    END LOOP;
END $$;

-- Configurar permisos para el rol Admin
DO $$
DECLARE
    admin_role_id UUID;
    admin_user_id UUID;
BEGIN
    SELECT id INTO admin_role_id FROM roles WHERE name = 'Admin';
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin';
    
    -- Admin puede hacer todo excepto gestionar el propio sistema de permisos
    INSERT INTO role_permissions (role_id, permission_id, granted_by)
    SELECT admin_role_id, p.id, admin_user_id
    FROM permissions p
    JOIN resources r ON p.resource_id = r.id
    WHERE r.name IN ('dashboard', 'users', 'roles', 'audit', 'settings');
END $$;

-- Configurar permisos para User Manager
DO $$
DECLARE
    user_manager_role_id UUID;
    admin_user_id UUID;
BEGIN
    SELECT id INTO user_manager_role_id FROM roles WHERE name = 'User Manager';
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin';
    
    INSERT INTO role_permissions (role_id, permission_id, granted_by)
    SELECT user_manager_role_id, p.id, admin_user_id
    FROM permissions p
    JOIN resources r ON p.resource_id = r.id
    WHERE r.name IN ('dashboard', 'users', 'roles') 
    AND p.action IN ('read', 'create', 'update');
END $$;

-- Configurar permisos para Auditor
DO $$
DECLARE
    auditor_role_id UUID;
    admin_user_id UUID;
BEGIN
    SELECT id INTO auditor_role_id FROM roles WHERE name = 'Auditor';
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin';
    
    INSERT INTO role_permissions (role_id, permission_id, granted_by)
    SELECT auditor_role_id, p.id, admin_user_id
    FROM permissions p
    JOIN resources r ON p.resource_id = r.id
    WHERE p.action = 'read';
END $$;

-- Configurar permisos básicos para User
DO $$
DECLARE
    user_role_id UUID;
    admin_user_id UUID;
BEGIN
    SELECT id INTO user_role_id FROM roles WHERE name = 'User';
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin';
    
    INSERT INTO role_permissions (role_id, permission_id, granted_by)
    SELECT user_role_id, p.id, admin_user_id
    FROM permissions p
    JOIN resources r ON p.resource_id = r.id
    WHERE r.name IN ('dashboard') AND p.action = 'read';
END $;
