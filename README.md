# Real Estate Investment Analysis Platform

Plataforma profesional para análisis de inversión inmobiliaria con scraping de portales, gestión de costos de construcción y análisis de rentabilidad.

**Sitio Web:** [https://real-estate-investment-theta.vercel.app/](https://real-estate-investment-theta.vercel.app/)

## 🏗️ Arquitectura

- **Backend**: FastAPI + PostgreSQL (PostGIS) + Celery + Redis
- **Frontend**: React + TypeScript + Material-UI + Vite
- **Base de Datos**: PostgreSQL 16 con extensión PostGIS
- **Cache & Queue**: Redis
- **Containerización**: Docker + Docker Compose

## 📋 Características

### Análisis de Mercado Inmobiliario
- Web scraping de portales (Argenprop, Zonaprop, Remax, MercadoLibre)
- Seguimiento automático de cambios de precio
- Registro de visitas presenciales
- Análisis geoespacial con mapas interactivos
- Gráficos y visualizaciones de tendencias

### Gestión de Costos de Construcción
- Registro de materiales y mano de obra
- Actualización automática de precios
- Historial de cambios
- Análisis de cotizaciones

### Análisis de Inversión
- Cálculo de ROI
- Proyecciones de rentabilidad
- Seguimiento de proyectos
- Reportes en PDF

## 🚀 Inicio Rápido

### Prerrequisitos

- Docker y Docker Compose
- Node.js 20+ (para desarrollo local)
- Python 3.12+ (para desarrollo local)

### Instalación con Docker

1. Clonar el repositorio
```bash
cd "proyecto inmobiliario"
```

2. Copiar archivos de configuración
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

3. Iniciar servicios con Docker Compose
```bash
docker-compose up -d
```

4. Ejecutar migraciones de base de datos
```bash
docker-compose exec backend alembic upgrade head
```

5. Acceder a la aplicación
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/v1/docs

### Desarrollo Local

#### Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar configuración
cp .env.example .env

# Ejecutar migraciones
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Copiar configuración
cp .env.example .env

# Iniciar servidor de desarrollo
npm run dev
```

## 📁 Estructura del Proyecto

```
proyecto-inmobiliario/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints REST
│   │   ├── core/         # Configuración y seguridad
│   │   ├── models/       # Modelos SQLAlchemy
│   │   ├── schemas/      # Schemas Pydantic
│   │   ├── services/     # Lógica de negocio
│   │   ├── scrapers/     # Web scrapers
│   │   └── tasks/        # Tareas Celery
│   ├── alembic/          # Migraciones
│   └── tests/            # Tests
├── frontend/
│   ├── src/
│   │   ├── api/          # Cliente API
│   │   ├── components/   # Componentes reutilizables
│   │   ├── features/     # Módulos por funcionalidad
│   │   ├── store/        # Estado global (Zustand)
│   │   └── styles/       # Tema y estilos
│   └── public/
└── docker-compose.yml
```

## 🔧 Configuración

### Variables de Entorno - Backend

Ver `backend/.env.example` para todas las opciones disponibles.

Principales configuraciones:
- `SECRET_KEY`: Clave secreta para JWT (cambiar en producción)
- `DATABASE_URL`: URL de conexión a PostgreSQL
- `REDIS_URL`: URL de conexión a Redis

### Variables de Entorno - Frontend

Ver `frontend/.env.example` para todas las opciones.

## 📚 API Documentation

La documentación interactiva de la API está disponible en:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## 🧪 Testing

### Backend
```bash
cd backend
pytest
```

### Frontend
```bash
cd frontend
npm run test
```

## 🚢 Deployment

### Opción 1: Deployment Gratuito (Recomendado para inicio)

Stack gratuito completo:
- **Frontend**: Vercel (gratis forever)
- **Backend**: Render Free Tier (gratis con sleep después de 15 min)
- **Database**: Supabase (gratis, 500MB con PostGIS)
- **Redis**: Upstash (gratis, 10k commands/día)

**Limitación principal**: El backend se duerme después de 15 min de inactividad. La primera request tarda ~30-60 segundos en despertar.

Ver documentación completa en `.claude/plans/` para pasos detallados.

### Opción 2: Producción con Docker

1. Actualizar variables de entorno en archivos `.env`
2. Construir imágenes de producción:
```bash
docker-compose -f docker-compose.prod.yml build
```

3. Iniciar servicios:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 📝 Roadmap

- [x] Estructura base del proyecto
- [x] Autenticación y autorización
- [x] Modelos de base de datos
- [ ] Web scrapers para portales inmobiliarios
- [ ] Dashboard con analytics
- [ ] Mapas interactivos
- [ ] Generación de reportes PDF
- [ ] Notificaciones de cambios de precio
- [ ] App móvil (futuro)

## 🤝 Contribución

Este es un proyecto privado de desarrollo profesional.

## 📄 Licencia

Privado - Todos los derechos reservados

## 👤 Autor

Desarrollado como proyecto profesional de análisis inmobiliario.

