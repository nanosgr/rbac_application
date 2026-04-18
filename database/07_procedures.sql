-- =====================================
-- RBAC Stored Procedures
-- =====================================

SET search_path TO rbac, public;

-- Procedimiento para crear un nuevo usuario con rol
CREATE OR REPLACE FUNCTION create_user_with_role(
    p_username VARCHAR(50),
    p_email VARCHAR(255),
    p_password VARCHAR(255),
    p_first_name VARCHAR(100),
    p_last_name VARCHAR(100),
    p_role_name VARCHAR(50),
    p_created_by UUID DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    new_user_id UUID;
    role_id UUID;
BEGIN
    -- Crear el usuario
    INSERT INTO users (username, email, password_hash, first_name, last_name, created_by)
    VALUES (p_username, p_email, crypt(p_password, gen_salt('bf')), p_first_name, p_last_name, p_created_by)
    RETURNING id INTO new_user_id;
    
    -- Obtener el ID del rol
    SELECT id INTO role_id FROM roles WHERE name = p_role_name AND is_active = TRUE;
    
    IF role_id IS NULL THEN
        RAISE EXCEPTION 'Role % not found or inactive', p_role_name;
    END IF;
    
    -- Asignar el rol al usuario
    INSERT INTO user_roles (user_id, role_id, assigned_by)
    VALUES (new_user_id, role_id, p_created_by);
    
    RETURN new_user_id;
END;
$$ LANGUAGE plpgsql;

-- Procedimiento para cambiar contraseña de usuario
CREATE OR REPLACE FUNCTION change_user_password(
    p_user_id UUID,
    p_old_password VARCHAR(255),
    p_new_password VARCHAR(255)
)
RETURNS BOOLEAN AS $$
DECLARE
    current_hash VARCHAR(255);
BEGIN
    -- Obtener el hash actual
    SELECT password_hash INTO current_hash FROM users WHERE id = p_user_id;
    
    IF current_hash IS NULL THEN
        RAISE EXCEPTION 'User not found';
    END IF;
    
    -- Verificar la contraseña actual
    IF current_hash != crypt(p_old_password, current_hash) THEN
        RETURN FALSE;
    END IF;
    
    -- Actualizar con la nueva contraseña
    UPDATE users 
    SET password_hash = crypt(p_new_password, gen_salt('bf')),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_user_id;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Procedimiento para bloquear/desbloquear usuario
CREATE OR REPLACE FUNCTION toggle_user_status(
    p_user_id UUID,
    p_is_active BOOLEAN,
    p_updated_by UUID DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE users 
    SET is_active = p_is_active,
        updated_by = p_updated_by,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_user_id;
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    -- Si se desactiva el usuario, desactivar también sus sesiones
    IF p_is_active = FALSE THEN
        UPDATE user_sessions 
        SET is_active = FALSE 
        WHERE user_id = p_user_id;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Procedimiento para asignar rol a usuario
CREATE OR REPLACE FUNCTION assign_role_to_user(
    p_user_id UUID,
    p_role_name VARCHAR(50),
    p_assigned_by UUID,
    p_expires_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    role_id UUID;
BEGIN
    -- Obtener ID del rol
    SELECT id INTO role_id FROM roles WHERE name = p_role_name AND is_active = TRUE;
    
    IF role_id IS NULL THEN
        RAISE EXCEPTION 'Role % not found or inactive', p_role_name;
    END IF;
    
    -- Insertar o actualizar la asignación
    INSERT INTO user_roles (user_id, role_id, assigned_by, expires_at)
    VALUES (p_user_id, role_id, p_assigned_by, p_expires_at)
    ON CONFLICT (user_id, role_id) 
    DO UPDATE SET 
        is_active = TRUE,
        assigned_by = p_assigned_by,
        assigned_at = CURRENT_TIMESTAMP,
        expires_at = p_expires_at;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Procedimiento para revocar rol de usuario
CREATE OR REPLACE FUNCTION revoke_role_from_user(
    p_user_id UUID,
    p_role_name VARCHAR(50)
)
RETURNS BOOLEAN AS $$
DECLARE
    role_id UUID;
BEGIN
    -- Obtener ID del rol
    SELECT id INTO role_id FROM roles WHERE name = p_role_name;
    
    IF role_id IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Desactivar la asignación
    UPDATE user_roles 
    SET is_active = FALSE 
    WHERE user_id = p_user_id AND role_id = role_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Procedimiento para asignar permiso a rol
CREATE OR REPLACE FUNCTION assign_permission_to_role(
    p_role_name VARCHAR(50),
    p_permission_name VARCHAR(100),
    p_action VARCHAR(50),
    p_resource_name VARCHAR(100),
    p_granted_by UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    role_id UUID;
    permission_id UUID;
BEGIN
    -- Obtener ID del rol
    SELECT id INTO role_id FROM roles WHERE name = p_role_name AND is_active = TRUE;
    
    IF role_id IS NULL THEN
        RAISE EXCEPTION 'Role % not found or inactive', p_role_name;
    END IF;
    
    -- Obtener ID del permiso
    SELECT p.id INTO permission_id 
    FROM permissions p
    JOIN resources r ON p.resource_id = r.id
    WHERE p.name = p_permission_name 
    AND p.action = p_action 
    AND r.name = p_resource_name
    AND p.is_active = TRUE 
    AND r.is_active = TRUE;
    
    IF permission_id IS NULL THEN
        RAISE EXCEPTION 'Permission %:% on resource % not found or inactive', 
                       p_permission_name, p_action, p_resource_name;
    END IF;
    
    -- Insertar o actualizar la asignación
    INSERT INTO role_permissions (role_id, permission_id, granted_by)
    VALUES (role_id, permission_id, p_granted_by)
    ON CONFLICT (role_id, permission_id) 
    DO UPDATE SET 
        is_active = TRUE,
        granted_by = p_granted_by,
        granted_at = CURRENT_TIMESTAMP;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Procedimiento para registrar actividad de sesión
CREATE OR REPLACE FUNCTION update_session_activity(
    p_session_token VARCHAR(255)
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE user_sessions 
    SET last_activity = CURRENT_TIMESTAMP 
    WHERE session_token = p_session_token 
    AND is_active = TRUE 
    AND expires_at > CURRENT_TIMESTAMP;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Procedimiento para crear sesión de usuario
CREATE OR REPLACE FUNCTION create_user_session(
    p_user_id UUID,
    p_session_token VARCHAR(255),
    p_refresh_token VARCHAR(255),
    p_ip_address INET,
    p_user_agent TEXT,
    p_expires_at TIMESTAMP WITH TIME ZONE
)
RETURNS UUID AS $$
DECLARE
    session_id UUID;
BEGIN
    -- Limpiar sesiones expiradas del usuario
    DELETE FROM user_sessions 
    WHERE user_id = p_user_id 
    AND (expires_at < CURRENT_TIMESTAMP OR is_active = FALSE);
    
    -- Crear nueva sesión
    INSERT INTO user_sessions (user_id, session_token, refresh_token, ip_address, user_agent, expires_at)
    VALUES (p_user_id, p_session_token, p_refresh_token, p_ip_address, p_user_agent, p_expires_at)
    RETURNING id INTO session_id;
    
    RETURN session_id;
END;
$$ LANGUAGE plpgsql;

-- Procedimiento para obtener menú de usuario basado en permisos
CREATE OR REPLACE FUNCTION get_user_menu(p_user_id UUID)
RETURNS TABLE(
    resource_id UUID,
    resource_name VARCHAR,
    resource_path VARCHAR,
    resource_icon VARCHAR,
    parent_id UUID,
    sort_order INTEGER,
    level INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE user_resources AS (
        -- Recursos a los que el usuario tiene acceso
        SELECT DISTINCT r.id, r.parent_id
        FROM resources r
        JOIN permissions p ON r.id = p.resource_id
        WHERE p.id IN (
            SELECT DISTINCT permission_id 
            FROM get_user_permissions(p_user_id)
            JOIN permissions perm ON perm.name = get_user_permissions.permission_name 
                AND perm.action = get_user_permissions.action
            JOIN resources res ON perm.resource_id = res.id 
                AND res.name = get_user_permissions.resource_name
        )
        AND r.is_active = TRUE
        
        UNION
        
        -- Incluir recursos padre necesarios para la navegación
        SELECT r.id, r.parent_id
        FROM resources r
        JOIN user_resources ur ON r.id = ur.parent_id
        WHERE r.is_active = TRUE
    ),
    menu_tree AS (
        -- Nodos raíz
        SELECT 
            r.id, r.name, r.path, r.icon, r.parent_id, r.sort_order, 0 as level
        FROM resources r
        JOIN user_resources ur ON r.id = ur.id
        WHERE r.parent_id IS NULL
        
        UNION ALL
        
        -- Nodos hijos
        SELECT 
            r.id, r.name, r.path, r.icon, r.parent_id, r.sort_order, mt.level + 1
        FROM resources r
        JOIN user_resources ur ON r.id = ur.id
        JOIN menu_tree mt ON r.parent_id = mt.id
    )
    SELECT mt.id, mt.name, mt.path, mt.icon, mt.parent_id, mt.sort_order, mt.level
    FROM menu_tree mt
    ORDER BY mt.level, mt.sort_order;
END;
$$ LANGUAGE plpgsql;
