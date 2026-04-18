# RBAC Application - Guía de Inicio Rápido

## Descripción

Aplicación completa de Control de Acceso Basado en Roles (RBAC) con:
- **Backend**: FastAPI + PostgreSQL
- **Frontend**: Next.js + TypeScript + Tailwind CSS

## Requisitos Previos

- Python 3.8+
- Node.js 18.18.0+
- PostgreSQL 17+
- npm o yarn

## Instalación Completa

### 1. Configurar Base de Datos

```bash
cd database
chmod +x setup_database.sh
./setup_database.sh
```

**Credenciales de BD:**
- Database: `rbac_app`
- Usuario: `rbac_user`
- Password: `rbac_password`

### 2. Configurar Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Inicializar datos
python -c "from app.db.init_db import create_tables, init_db; create_tables(); init_db()"
```

### 3. Configurar Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
```

## Ejecutar la Aplicación

### Terminal 1: Backend
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**API disponible en:** http://localhost:8000
**Documentación:** http://localhost:8000/docs

### Terminal 2: Frontend
```bash
cd frontend
npm run dev
```

**Aplicación disponible en:** http://localhost:3000

## Usuarios de Prueba

| Usuario    | Contraseña | Rol         | Permisos |
|------------|------------|-------------|----------|
| superadmin | admin123   | Super Admin | Todos    |
| admin      | admin123   | Admin       | Casi todos |
| manager    | manager123 | Manager     | Lectura + algunos de escritura |
| user       | user123    | User        | Solo lectura básica |

## Estructura del Proyecto

```
rbac_application/
├── backend/              # FastAPI Backend
│   ├── app/
│   │   ├── api/         # Endpoints REST
│   │   ├── core/        # Configuración y seguridad
│   │   ├── models/      # Modelos SQLAlchemy
│   │   ├── schemas/     # Schemas Pydantic
│   │   └── services/    # Lógica de negocio
│   └── alembic/         # Migraciones
├── database/            # Scripts SQL PostgreSQL
│   ├── 01-07_*.sql     # Scripts de inicialización
│   └── setup_database.sh
└── frontend/            # Next.js Frontend
    ├── app/             # App Router
    ├── components/      # Componentes React
    ├── context/         # Context providers
    ├── lib/             # API client y servicios
    └── types/           # TypeScript types
```

## Funcionalidades Principales

### Dashboard
- Panel de control con estadísticas
- Usuarios recientes
- Permisos del usuario actual
- Acciones rápidas

### Gestión de Usuarios
- CRUD completo
- Asignación de roles
- Activar/desactivar usuarios

### Gestión de Roles
- CRUD completo
- Asignación de permisos agrupados por recurso
- Visualización de permisos por rol

### Gestión de Permisos
- CRUD completo
- Formato: `recurso:acción`
- Vista agrupada por recurso

## Sistema de Permisos

Los permisos siguen el formato `recurso:acción`:

**Recursos:**
- `users` - Gestión de usuarios
- `roles` - Gestión de roles
- `permissions` - Gestión de permisos
- `dashboard` - Panel de control
- `reports` - Reportes

**Acciones:**
- `create` - Crear
- `read` - Leer/ver
- `update` - Actualizar
- `delete` - Eliminar

**Ejemplos:**
- `users:read` - Ver usuarios
- `roles:create` - Crear roles
- `permissions:delete` - Eliminar permisos

## Control de Acceso en Frontend

El frontend usa el componente `ProtectedComponent` para mostrar/ocultar elementos:

```tsx
<ProtectedComponent permissions={['users:create']}>
  <Button onClick={handleCreate}>Crear Usuario</Button>
</ProtectedComponent>
```

## Troubleshooting

### Error de conexión a PostgreSQL
```bash
sudo systemctl status postgresql
sudo systemctl start postgresql
```

### Error en el backend
- Verificar que el venv esté activado
- Verificar credenciales de BD en backend/.env

### Error en el frontend
- Verificar que el backend esté corriendo
- Verificar NEXT_PUBLIC_API_URL en frontend/.env.local

### Reinstalar base de datos
```bash
sudo -u postgres psql
DROP DATABASE IF EXISTS rbac_app;
DROP USER IF EXISTS rbac_user;
\q

cd database
./setup_database.sh
```

## Documentación Adicional

- **Backend**: Ver `backend/README.md`
- **Frontend**: Ver `frontend/README.md`
- **Database**: Ver `database/README.md`
- **Arquitectura**: Ver `CLAUDE.md`

## Tecnologías Utilizadas

**Backend:**
- FastAPI 0.104.1
- SQLAlchemy 2.0.23
- PostgreSQL 17
- JWT Authentication
- Alembic (migraciones)

**Frontend:**
- Next.js 15
- TypeScript
- Tailwind CSS
- React Context API

## Próximos Pasos

1. Iniciar sesión con uno de los usuarios de prueba
2. Explorar el dashboard
3. Probar CRUD de usuarios, roles y permisos
4. Cambiar entre usuarios para ver diferentes permisos
5. Personalizar según tus necesidades

## Seguridad en Producción

⚠️ **IMPORTANTE**: Antes de desplegar a producción:

1. Cambiar `SECRET_KEY` en backend/.env
2. Cambiar contraseñas de usuarios por defecto
3. Cambiar credenciales de base de datos
4. Configurar CORS apropiadamente
5. Usar HTTPS
6. Configurar variables de entorno seguras

## Soporte

Para reportar problemas o contribuir, consultar la documentación específica de cada componente.

---

¡Listo para comenzar! 🚀
