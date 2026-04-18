-- =====================================
-- RBAC Functions and Triggers
-- =====================================

SET search_path TO rbac, public;

-- Función para actualizar el campo updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para actualizar updated_at automáticamente
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_resources_updated_at BEFORE UPDATE ON resources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_permissions_updated_at BEFORE UPDATE ON permissions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Función para limpiar sesiones expiradas
CREATE OR REPLACE FUNCTION clean_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions 
    WHERE expires_at < CURRENT_TIMESTAMP OR is_active = FALSE;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Función para verificar si un usuario tiene un permiso específico
CREATE OR REPLACE FUNCTION user_has_permission(
    p_user_id UUID,
    p_permission_name VARCHAR,
    p_action VARCHAR,
    p_resource_name VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    has_permission BOOLEAN := FALSE;
    permission_denied BOOLEAN := FALSE;
BEGIN
    -- Verificar si hay una denegación explícita (user_permissions con DENY)
    SELECT EXISTS(
        SELECT 1 
        FROM user_permissions up
        JOIN permissions p ON up.permission_id = p.id
        JOIN resources r ON p.resource_id = r.id
        WHERE up.user_id = p_user_id
        AND p.name = p_permission_name
        AND p.action = p_action
        AND r.name = p_resource_name
        AND up.permission_type = 'DENY'
        AND up.is_active = TRUE
        AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
    ) INTO permission_denied;
    
    -- Si hay denegación explícita, retornar FALSE
    IF permission_denied THEN
        RETURN FALSE;
    END IF;
    
    -- Verificar permisos a través de roles
    SELECT EXISTS(
        SELECT 1
        FROM user_roles ur
        JOIN role_permissions rp ON ur.role_id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.id
        JOIN resources r ON p.resource_id = r.id
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
    
    -- Si no tiene permiso por roles, verificar permisos directos (GRANT)
    IF NOT has_permission THEN
        SELECT EXISTS(
            SELECT 1 
            FROM user_permissions up
            JOIN permissions p ON up.permission_id = p.id
            JOIN resources r ON p.resource_id = r.id
            WHERE up.user_id = p_user_id
            AND p.name = p_permission_name
            AND p.action = p_action
            AND r.name = p_resource_name
            AND up.permission_type = 'GRANT'
            AND up.is_active = TRUE
            AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
        ) INTO has_permission;
    END IF;
    
    RETURN has_permission;
END;
$$ LANGUAGE plpgsql;

-- Función para obtener todos los permisos de un usuario
CREATE OR REPLACE FUNCTION get_user_permissions(p_user_id UUID)
RETURNS TABLE(
    resource_name VARCHAR,
    permission_name VARCHAR,
    action VARCHAR,
    source VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    -- Permisos por roles
    SELECT DISTINCT
        r.name as resource_name,
        p.name as permission_name,
        p.action,
        'ROLE' as source
    FROM user_roles ur
    JOIN role_permissions rp ON ur.role_id = rp.role_id
    JOIN permissions p ON rp.permission_id = p.id
    JOIN resources r ON p.resource_id = r.id
    WHERE ur.user_id = p_user_id
    AND ur.is_active = TRUE
    AND rp.is_active = TRUE
    AND p.is_active = TRUE
    AND r.is_active = TRUE
    AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
    
    UNION
    
    -- Permisos directos (solo GRANT)
    SELECT DISTINCT
        r.name as resource_name,
        p.name as permission_name,
        p.action,
        'DIRECT' as source
    FROM user_permissions up
    JOIN permissions p ON up.permission_id = p.id
    JOIN resources r ON p.resource_id = r.id
    WHERE up.user_id = p_user_id
    AND up.permission_type = 'GRANT'
    AND up.is_active = TRUE
    AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
    
    -- Excluir permisos denegados explícitamente
    EXCEPT
    
    SELECT DISTINCT
        r.name as resource_name,
        p.name as permission_name,
        p.action,
        'DENIED' as source
    FROM user_permissions up
    JOIN permissions p ON up.permission_id = p.id
    JOIN resources r ON p.resource_id = r.id
    WHERE up.user_id = p_user_id
    AND up.permission_type = 'DENY'
    AND up.is_active = TRUE
    AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP);
END;
$$ LANGUAGE plpgsql;

-- Función para auditoría automática
CREATE OR REPLACE FUNCTION audit_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (action, resource_type, resource_id, old_values, timestamp)
        VALUES ('DELETE', TG_TABLE_NAME, OLD.id, row_to_json(OLD), CURRENT_TIMESTAMP);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (action, resource_type, resource_id, old_values, new_values, timestamp)
        VALUES ('UPDATE', TG_TABLE_NAME, NEW.id, row_to_json(OLD), row_to_json(NEW), CURRENT_TIMESTAMP);
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (action, resource_type, resource_id, new_values, timestamp)
        VALUES ('INSERT', TG_TABLE_NAME, NEW.id, row_to_json(NEW), CURRENT_TIMESTAMP);
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Aplicar triggers de auditoría a las tablas principales
CREATE TRIGGER audit_users_changes
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION audit_changes();

CREATE TRIGGER audit_roles_changes
    AFTER INSERT OR UPDATE OR DELETE ON roles
    FOR EACH ROW EXECUTE FUNCTION audit_changes();

CREATE TRIGGER audit_user_roles_changes
    AFTER INSERT OR UPDATE OR DELETE ON user_roles
    FOR EACH ROW EXECUTE FUNCTION audit_changes();

CREATE TRIGGER audit_role_permissions_changes
    AFTER INSERT OR UPDATE OR DELETE ON role_permissions
    FOR EACH ROW EXECUTE FUNCTION audit_changes();

CREATE TRIGGER audit_user_permissions_changes
    AFTER INSERT OR UPDATE OR DELETE ON user_permissions
    FOR EACH ROW EXECUTE FUNCTION audit_changes();
