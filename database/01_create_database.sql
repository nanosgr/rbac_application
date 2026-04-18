-- =====================================
-- RBAC Application Database Creation
-- PostgreSQL 17
-- =====================================

-- Crear la base de datos (ejecutar como superusuario)
-- CREATE DATABASE rbac_app;

-- Conectar a la base de datos rbac_app antes de ejecutar el resto
-- \c rbac_app;

-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Crear esquema para la aplicación
CREATE SCHEMA IF NOT EXISTS rbac;

-- Configurar search_path para incluir el esquema rbac
SET search_path TO rbac, public;

COMMENT ON SCHEMA rbac IS 'Esquema para el sistema de control de acceso basado en roles (RBAC)';
