-- =====================================
-- RBAC Views for easier data access
-- =====================================

SET search_path TO rbac, public;

-- Vista para mostrar usuarios con sus roles
CREATE VIEW user_roles_view AS
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
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
WHERE u.is_active = TRUE;

-- Vista para mostrar roles con sus permisos
CREATE VIEW role_permissions_view AS
SELECT 
    r.id as role_id,
    r.name as role_name,
    r.description as role_description,
    res.id as resource_id,
    res.name as resource_name,
    res.description as resource_description,
    p.id as permission_id,
    p.name as permission_name,
    p.action as permission_action,
    p.description as permission_description,
    rp.granted_at
FROM roles r
LEFT JOIN role_permissions rp ON r.id = rp.role_id
LEFT JOIN permissions p ON rp.permission_id = p.id
LEFT JOIN resources res ON p.resource_id = res.id
WHERE r.is_active = TRUE 
AND (rp.is_active IS NULL OR rp.is_active = TRUE)
AND (p.is_active IS NULL OR p.is_active = TRUE)
AND (res.is_active IS NULL OR res.is_active = TRUE);

-- Vista para mostrar todos los permisos efectivos de un usuario
CREATE VIEW user_effective_permissions AS
SELECT DISTINCT
    u.id as user_id,
    u.username,
    res.name as resource_name,
    p.name as permission_name,
    p.action as permission_action,
    'ROLE' as permission_source,
    r.name as source_name
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
JOIN role_permissions rp ON r.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id
JOIN resources res ON p.resource_id = res.id
WHERE u.is_active = TRUE
AND ur.is_active = TRUE
AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
AND rp.is_active = TRUE
AND p.is_active = TRUE
AND res.is_active = TRUE

UNION

SELECT DISTINCT
    u.id as user_id,
    u.username,
    res.name as resource_name,
    p.name as permission_name,
    p.action as permission_action,
    'DIRECT' as permission_source,
    'Direct Assignment' as source_name
FROM users u
JOIN user_permissions up ON u.id = up.user_id
JOIN permissions p ON up.permission_id = p.id
JOIN resources res ON p.resource_id = res.id
WHERE u.is_active = TRUE
AND up.is_active = TRUE
AND up.permission_type = 'GRANT'
AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
AND p.is_active = TRUE
AND res.is_active = TRUE;

-- Vista para mostrar recursos en estructura jerárquica
CREATE VIEW resources_hierarchy AS
WITH RECURSIVE resource_tree AS (
    -- Nodos raíz (sin padre)
    SELECT 
        id,
        name,
        description,
        resource_type,
        parent_id,
        path,
        icon,
        sort_order,
        0 as level,
        ARRAY[sort_order] as sort_path,
        name as full_path
    FROM resources 
    WHERE parent_id IS NULL AND is_active = TRUE
    
    UNION ALL
    
    -- Nodos hijos
    SELECT 
        r.id,
        r.name,
        r.description,
        r.resource_type,
        r.parent_id,
        r.path,
        r.icon,
        r.sort_order,
        rt.level + 1,
        rt.sort_path || r.sort_order,
        rt.full_path || ' > ' || r.name
    FROM resources r
    JOIN resource_tree rt ON r.parent_id = rt.id
    WHERE r.is_active = TRUE
)
SELECT * FROM resource_tree ORDER BY sort_path;

-- Vista para mostrar sesiones activas de usuarios
CREATE VIEW active_user_sessions AS
SELECT 
    u.id as user_id,
    u.username,
    u.email,
    u.first_name,
    u.last_name,
    s.id as session_id,
    s.session_token,
    s.ip_address,
    s.user_agent,
    s.created_at as session_created,
    s.last_activity,
    s.expires_at
FROM users u
JOIN user_sessions s ON u.id = s.user_id
WHERE s.is_active = TRUE 
AND s.expires_at > CURRENT_TIMESTAMP
ORDER BY s.last_activity DESC;

-- Vista para auditoría con información de usuarios
CREATE VIEW audit_log_detailed AS
SELECT 
    al.id,
    al.action,
    al.resource_type,
    al.resource_id,
    al.old_values,
    al.new_values,
    al.ip_address,
    al.user_agent,
    al.timestamp,
    u.username,
    u.email,
    u.first_name,
    u.last_name
FROM audit_log al
LEFT JOIN users u ON al.user_id = u.id
ORDER BY al.timestamp DESC;

-- Vista para mostrar estadísticas del sistema
CREATE VIEW system_stats AS
SELECT 
    (SELECT COUNT(*) FROM users WHERE is_active = TRUE) as active_users,
    (SELECT COUNT(*) FROM users WHERE is_active = FALSE) as inactive_users,
    (SELECT COUNT(*) FROM roles WHERE is_active = TRUE) as active_roles,
    (SELECT COUNT(*) FROM permissions WHERE is_active = TRUE) as active_permissions,
    (SELECT COUNT(*) FROM resources WHERE is_active = TRUE) as active_resources,
    (SELECT COUNT(*) FROM user_sessions WHERE is_active = TRUE AND expires_at > CURRENT_TIMESTAMP) as active_sessions,
    (SELECT COUNT(*) FROM audit_log WHERE timestamp >= CURRENT_DATE) as today_audit_entries;
