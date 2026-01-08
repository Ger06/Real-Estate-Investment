# Backend Setup - Guía Rápida

## 📋 Requisitos Previos

Para ejecutar el backend localmente necesitas:

1. **PostgreSQL 16+** con extensión PostGIS instalada
2. **Redis** (opcional para desarrollo básico)
3. **Python 3.12+**

## 🚀 Opción 1: Desarrollo con Docker (Recomendado)

La forma más fácil es usar Docker Compose desde la raíz del proyecto:

```bash
# Desde la raíz del proyecto
cd ..
docker-compose up -d

# Ejecutar migraciones
docker-compose exec backend alembic upgrade head

# Ver logs
docker-compose logs -f backend
```

## 💻 Opción 2: Desarrollo Local

### 1. Instalar PostgreSQL con PostGIS

**Windows:**
- Descargar PostgreSQL desde: https://www.postgresql.org/download/windows/
- Durante la instalación, incluir PostGIS desde Stack Builder

**Crear base de datos:**
```sql
CREATE DATABASE real_estate_db;
\c real_estate_db
CREATE EXTENSION postgis;
```

### 2. Configurar Entorno Python

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno

El archivo `.env` ya está configurado para desarrollo local. Verifica que los valores sean correctos:

```env
# Database - LOCAL DEVELOPMENT
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres  # Cambia esto si usaste otra contraseña
POSTGRES_DB=real_estate_db
POSTGRES_PORT=5432
```

### 4. Ejecutar Migraciones

```bash
# Crear migración inicial
alembic revision --autogenerate -m "Initial migration"

# Aplicar migraciones
alembic upgrade head
```

### 5. Iniciar Servidor

```bash
# Modo desarrollo con hot reload
uvicorn app.main:app --reload

# O usando Python directamente
python -m app.main
```

El servidor estará disponible en:
- API: http://localhost:8000
- Documentación: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## 🔧 Solución de Problemas

### Error: "error parsing value for field BACKEND_CORS_ORIGINS"

Si ves este error, asegúrate de que el archivo `.env` tenga el formato correcto:
```env
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8000
```

### Error: "could not connect to server"

Verifica que PostgreSQL esté corriendo:
```bash
# Windows
Get-Service postgresql*

# Verificar conexión
psql -U postgres -d real_estate_db
```

### Error: "extension postgis does not exist"

Instala PostGIS en tu base de datos:
```sql
CREATE EXTENSION postgis;
```

## 📚 Comandos Útiles

```bash
# Ver migraciones
alembic history

# Revertir última migración
alembic downgrade -1

# Crear nueva migración
alembic revision --autogenerate -m "Descripción del cambio"

# Tests
pytest

# Formatear código
black app/

# Linting
flake8 app/
mypy app/
```

## 🎯 Próximos Pasos

1. ✅ Instalar dependencias
2. ✅ Configurar base de datos
3. ⏳ Ejecutar migraciones
4. ⏳ Iniciar servidor
5. ⏳ Probar API en /docs
6. ⏳ Registrar primer usuario
7. ⏳ Comenzar desarrollo de features

## 📖 Estructura del Proyecto

```
backend/
├── app/
│   ├── api/v1/          # Endpoints REST
│   ├── core/            # Configuración y seguridad
│   ├── models/          # Modelos SQLAlchemy
│   ├── schemas/         # Schemas Pydantic
│   ├── services/        # Lógica de negocio
│   ├── scrapers/        # Web scrapers
│   └── tasks/           # Tareas Celery
├── alembic/             # Migraciones
├── tests/               # Tests
├── .env                 # Variables de entorno (no commitear)
├── .env.example         # Template de variables
├── requirements.txt     # Dependencias Python
└── README.md            # Este archivo
```

## 🔐 Seguridad

**IMPORTANTE**: Antes de desplegar a producción:

1. Cambiar `SECRET_KEY` en `.env`:
   ```bash
   openssl rand -hex 32
   ```

2. Cambiar contraseñas de base de datos

3. Actualizar `FIRST_SUPERUSER_EMAIL` y `FIRST_SUPERUSER_PASSWORD`

4. Configurar CORS apropiadamente

5. Usar HTTPS en producción
