-- =====================================
-- Test Queries for RBAC System
-- =====================================

SET search_path TO rbac, public;

-- Test 1: Verificar estructura de tablas
\echo '=== TEST 1: Verificar estructura de tablas ==='
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'rbac'
ORDER BY tablename;

-- Test 2: Contar registros en tablas principales
\echo '=== TEST 2: Contar registros en tablas principales ==='
SELECT 
    'users' as tabla,
    COUNT(*) as registros
FROM users
UNION ALL
SELECT 'roles', COUNT(*) FROM roles
UNION ALL
SELECT 'resources', COUNT(*) FROM resources
UNION ALL
SELECT 'permissions', COUNT(*) FROM permissions
UNION ALL
SELECT 'user_roles', COUNT(*) FROM user_roles
UNION ALL
SELECT 'role_permissions', COUNT(*) FROM role_permissions;

-- Test 3: Verificar usuario admin y sus roles
\echo '=== TEST 3: Usuario admin y sus roles ==='
SELECT 
    u.username,
    u.email,
    u.first_name,
    u.last_name,
    r.name as role_name,
    ur.assigned_at
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
WHERE u.username = 'admin';

-- Test 4: Verificar permisos del rol Super Admin
\echo '=== TEST 4: Permisos del rol Super Admin ==='
SELECT 
    r.name as role_name,
    res.name as resource_name,
    p.name as permission_name,
    p.action
FROM roles r
JOIN role_permissions rp ON r.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id
JOIN resources res ON p.resource_id = res.id
WHERE r.name = 'Super Admin'
ORDER BY res.name, p.action;

-- Test 5: Probar función user_has_permission
\echo '=== TEST 5: Probar función user_has_permission ==='
DO $$
DECLARE
    admin_id UUID;
    has_perm BOOLEAN;
BEGIN
    -- Obtener ID del admin
    SELECT id INTO admin_id FROM users WHERE username = 'admin';
    
    -- Probar varios permisos
    SELECT user_has_permission(admin_id, 'dashboard_view', 'read', 'dashboard') INTO has_perm;
    RAISE NOTICE 'Admin tiene permiso dashboard_view: %', has_perm;
    
    SELECT user_has_permission(admin_id, 'users_create', 'create', 'users') INTO has_perm;
    RAISE NOTICE 'Admin tiene permiso users_create: %', has_perm;
    
    SELECT user_has_permission(admin_id, 'nonexistent', 'read', 'dashboard') INTO has_perm;
    RAISE NOTICE 'Admin tiene permiso inexistente: %', has_perm;
END $$;

-- Test 6: Probar función get_user_permissions
\echo '=== TEST 6: Permisos efectivos del usuario admin ==='
SELECT 
    resource_name,
    permission_name,
    action,
    source
FROM get_user_permissions((SELECT id FROM users WHERE username = 'admin'))
ORDER BY resource_name, permission_name;

-- Test 7: Verificar vistas
\echo '=== TEST 7: Verificar vistas creadas ==='
SELECT 
    schemaname,
    viewname,
    viewowner
FROM pg_views 
WHERE schemaname = 'rbac'
ORDER BY viewname;

-- Test 8: Probar vista user_roles_view
\echo '=== TEST 8: Vista user_roles_view ==='
SELECT * FROM user_roles_view LIMIT 5;

-- Test 9: Probar vista system_stats
\echo '=== TEST 9: Estadísticas del sistema ==='
SELECT * FROM system_stats;

-- Test 10: Probar creación de usuario con rol
\echo '=== TEST 10: Crear usuario de prueba ==='
DO $$
DECLARE
    new_user_id UUID;
    admin_id UUID;
BEGIN
    SELECT id INTO admin_id FROM users WHERE username = 'admin';
    
    -- Crear usuario de prueba
    SELECT create_user_with_role(
        'test_user',
        'test@example.com',
        'password123',
        'Test',
        'User',
        'User',
        admin_id
    ) INTO new_user_id;
    
    RAISE NOTICE 'Usuario de prueba creado con ID: %', new_user_id;
    
    -- Verificar que se creó correctamente
    IF EXISTS (SELECT 1 FROM users WHERE id = new_user_id) THEN
        RAISE NOTICE 'Usuario de prueba verificado exitosamente';
    ELSE
        RAISE NOTICE 'ERROR: Usuario de prueba no encontrado';
    END IF;
END $$;

-- Test 11: Probar cambio de contraseña
\echo '=== TEST 11: Probar cambio de contraseña ==='
DO $$
DECLARE
    test_user_id UUID;
    password_changed BOOLEAN;
BEGIN
    SELECT id INTO test_user_id FROM users WHERE username = 'test_user';
    
    SELECT change_user_password(test_user_id, 'password123', 'newpassword123') INTO password_changed;
    
    IF password_changed THEN
        RAISE NOTICE 'Contraseña cambiada exitosamente';
    ELSE
        RAISE NOTICE 'ERROR: No se pudo cambiar la contraseña';
    END IF;
END $$;

-- Test 12: Probar triggers de auditoría
\echo '=== TEST 12: Verificar auditoría ==='
-- Hacer una actualización para generar registro de auditoría
UPDATE users SET last_name = 'Updated' WHERE username = 'test_user';

-- Verificar que se registró en auditoría
SELECT 
    action,
    resource_type,
    timestamp,
    old_values->>'last_name' as old_last_name,
    new_values->>'last_name' as new_last_name
FROM audit_log 
WHERE resource_type = 'users' 
AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 minute'
ORDER BY timestamp DESC
LIMIT 1;

-- Test 13: Limpiar datos de prueba
\echo '=== TEST 13: Limpiar datos de prueba ==='
DELETE FROM users WHERE username = 'test_user';
\echo 'Usuario de prueba eliminado'

-- Test 14: Verificar funciones de limpieza
\echo '=== TEST 14: Probar limpieza de sesiones ==='
SELECT clean_expired_sessions() as sesiones_eliminadas;

-- Test 15: Rendimiento de consultas principales
\echo '=== TEST 15: Análisis de rendimiento ==='
EXPLAIN ANALYZE 
SELECT * FROM user_effective_permissions 
WHERE user_id = (SELECT id FROM users WHERE username = 'admin');

\echo '=== TESTS COMPLETADOS ==='
\echo 'Si todos los tests se ejecutaron sin errores, la instalación es exitosa.'
