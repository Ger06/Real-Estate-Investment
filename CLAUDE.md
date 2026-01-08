# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Real Estate Investment Analysis Platform - A professional platform for comprehensive real estate investment analysis in Argentina. The system integrates three core modules:

1. **Real Estate Market Analysis** - Web scraping from Argentine portals (Argenprop, Zonaprop, Remax, MercadoLibre) with automatic price tracking
2. **Construction Cost Management** - Material and labor cost tracking with automatic price updates
3. **Investment Analysis** - Combining market data and construction costs for complete investment ROI calculations

**Current State**: Replacing manual Excel-based workflow with automated, database-driven platform.

**Stack:**
- Backend: FastAPI + PostgreSQL (PostGIS) + SQLAlchemy (async) + Celery + Redis
- Frontend: React + TypeScript + Material-UI + Vite + Zustand
- Containerization: Docker + Docker Compose

## Development Commands

### Docker (Recommended)

From project root:

```bash
# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend alembic upgrade head

# View backend logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### Backend (Local Development)

From `backend/` directory:

```bash
# Setup virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# Start development server with hot reload
uvicorn app.main:app --reload

# Run tests
pytest

# Code quality
black app/          # Format code
flake8 app/         # Lint
mypy app/           # Type checking
```

Server runs at:
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

### Frontend (Local Development)

From `frontend/` directory:

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm preview

# Lint
npm run lint
```

Development server runs at http://localhost:5173

## Architecture & Code Organization

### Backend Architecture

**FastAPI Application Structure:**
- `app/main.py` - Application entry point with lifespan events, CORS, and middleware setup
- `app/database.py` - Async SQLAlchemy engine, session factory, and `get_db()` dependency
- `app/core/` - Core configuration and utilities
  - `config.py` - Pydantic Settings with environment variable management
  - `security.py` - JWT token creation/validation, password hashing
  - `logging.py` - Application logging setup
- `app/api/` - REST API endpoints
  - `deps.py` - Authentication dependencies (`get_current_user`, `get_current_active_superuser`)
  - `v1/router.py` - API router aggregating all endpoint modules
  - `v1/auth.py` - Authentication endpoints
  - `v1/properties.py` - Property CRUD and search
  - `v1/analytics.py` - Market analysis, charts, maps
  - `v1/costs.py` - Construction cost management
  - `v1/investments.py` - Investment project analysis

**Database Models (`app/models/`):**
- All models use `UUID` primary keys (PostgreSQL UUID type)
- `User` - Authentication and user management
- `Property` - Real estate listings with PostGIS geography for location data
  - Enums: `PropertySource` (argenprop, zonaprop, remax, mercadolibre, manual), `PropertyType` (casa, ph, departamento, terreno, local, oficina), `OperationType` (venta, alquiler, alquiler_temporal), `Currency` (USD, ARS), `PropertyStatus` (active, sold, rented, removed)
  - Related: `PropertyImage`, `PriceHistory`, `PropertyVisit`
- `Cost` - Construction materials and labor costs with price history
- Models use SQLAlchemy async patterns with relationships and cascade deletes

**Database Session Pattern:**
- Always use async sessions via `get_db()` dependency
- Sessions auto-commit on success, rollback on exception
- Use `select()` from sqlalchemy for queries, not legacy `Query` API

**Authentication Flow:**
- OAuth2 password bearer tokens (JWT)
- Token URL: `/api/v1/auth/login`
- Protected endpoints use `Depends(get_current_user)` dependency
- Superuser-only endpoints use `Depends(get_current_active_superuser)`

**Pydantic Schemas (`app/schemas/`):**
- Input validation and response serialization
- Separate schemas for create, update, and response models

**Background Tasks (`app/tasks/`):**
- Celery workers for async processing
- Celery Beat for scheduled tasks (periodic price checks)
- Use cases: web scraping, automatic price updates, price change notifications, PDF generation

**Web Scraping (`app/scrapers/`):**
- Scrapers for Argentine real estate portals: Argenprop, Zonaprop, Remax, MercadoLibre
- Selenium + BeautifulSoup for dynamic content
- Rate limiting and user agent rotation configured in settings
- Extract: photos, price, description, surfaces (covered, semi-covered, uncovered), floor level, property type, real estate agency, contact, zone

### Frontend Architecture

**React Application Structure:**
- `src/main.tsx` - Entry point
- `src/App.tsx` - Router setup with React Query provider, MUI theme provider, and protected routes
- `src/features/` - Feature-based organization
  - `auth/` - Login, registration
  - `dashboard/` - Main dashboard with analytics
  - `properties/` - Property list, detail, add/edit, map view
- `src/components/` - Reusable components (layout, charts, maps, filters)
- `src/store/` - Zustand stores for global state
  - `authStore.ts` - Authentication state management
- `src/api/` - API client with axios
- `src/styles/` - MUI theme configuration

**State Management:**
- Zustand for global state (authentication, user preferences)
- React Query (@tanstack/react-query) for server state management
- React Hook Form + Zod for form state and validation

**Routing Pattern:**
- React Router v6
- Protected routes wrapped with `ProtectedRoute` component checking `authStore.isAuthenticated`
- Layout component using Outlet for nested routes

**Data Fetching:**
- React Query configured with `refetchOnWindowFocus: false` and `retry: 1`
- Query client setup in App.tsx

### Database Schema Key Points

**PostGIS Integration:**
- `Property.location` uses `Geography(geometry_type='POINT', srid=4326)` for lat/lng
- GiST index on location field for spatial queries
- Map visualization with color-coded markers based on filters (price, type, zone)

**Price Tracking:**
- `PriceHistory` table tracks all price changes with timestamps
- Automatic percentage calculation on price changes
- Indexed by property_id + recorded_at for efficient time-series queries
- Scheduled Celery tasks check scraped URLs periodically and register price changes

**Property Data Storage:**
- Source URL tracked for automatic updates
- Multiple images per property (primary image flag, ordering)
- JSONB fields for amenities and contact info (flexible schema)
- Surface areas: covered_area, semi_covered_area, uncovered_area, total_area
- Calculated: price_per_sqm

**Visit Tracking:**
- `PropertyVisit` table for in-person visit notes
- Rating system (1-5 scale)
- Photo attachments from visits (JSONB array)
- Associated with user and property

## Core Business Logic

### Property Scraping Workflow

1. User provides URL from Argenprop, Zonaprop, Remax, or MercadoLibre
2. Backend extracts: photos, price, description, surfaces, floor, type, agency, contact, zone
3. Store in database with `source_url` and `source_id`
4. Optionally generate PDF report
5. Schedule periodic checks (Celery Beat) for price changes
6. On price change: create PriceHistory record, calculate change percentage

### Flexible Analysis Features

**Required Capabilities:**
- Dynamic filtering by: zone, price range, property type, operation type, surface area
- Visualizations: charts (price trends, price per m²), interactive maps with color-coding
- Calculated fields: price per m², estimated suggested price
- Comparison views: side-by-side property comparisons

### Construction Cost Management

- Track materials and labor costs
- Automatic price updates (likely via scraping or manual input with version history)
- Cost quotation sheets
- Progress tracking and certifications
- Historical cost data for trend analysis

### Investment Analysis Module

**Integration Point:**
- Combine property data (purchase price, location, characteristics) with construction costs
- Calculate total investment = property cost + construction/renovation costs
- ROI calculations based on rental income or resale estimates
- Project tracking through stages
- Feedback loop between market analysis and cost analysis

## Configuration

### Environment Variables

Backend (`backend/.env`):
- `SECRET_KEY` - JWT secret (change in production, use `openssl rand -hex 32`)
- `DATABASE_URL` - PostgreSQL connection (auto-built from POSTGRES_* vars)
- `REDIS_URL` - Redis connection for Celery
- `SCRAPING_USER_AGENT`, `SCRAPING_RATE_LIMIT`, `SCRAPING_TIMEOUT` - Scraping configuration
- CORS origins hardcoded in `config.py` for development

Frontend (`frontend/.env`):
- `VITE_API_URL` - Backend API URL (default: http://localhost:8000)
- `VITE_API_VERSION` - API version (default: v1)

### PostgreSQL Requirements

- PostgreSQL 16+ with PostGIS extension
- Create extension: `CREATE EXTENSION postgis;`
- Database specified in docker-compose.yml or local setup

## Development Guidelines

**Backend:**
- Use async/await patterns throughout
- All database operations must be async
- Use Pydantic v2 for schemas
- JWT tokens for authentication
- Follow FastAPI dependency injection patterns
- Use SQLAlchemy 2.0 syntax (no legacy Query API)

**Frontend:**
- TypeScript strict mode
- Material-UI v5 components
- React hooks patterns
- Controlled components with React Hook Form
- API calls through React Query
- Leaflet for map visualization with Recharts for analytics

**Database Migrations:**
- Always create migrations for schema changes: `alembic revision --autogenerate -m "message"`
- Review auto-generated migrations before applying
- Test migrations in development before production

**Web Scraping:**
- Respect rate limits (configured in settings)
- Handle dynamic content with Selenium
- Store raw HTML/data for debugging if needed
- Graceful error handling when sites change structure
- Log scraping failures for monitoring

**Async Patterns:**
- Backend uses `asyncpg` driver for PostgreSQL
- All route handlers should be async
- Database sessions from `get_db()` are async context managers

## Known Patterns

### Adding New API Endpoints

1. Create Pydantic schemas in `app/schemas/`
2. Create/update SQLAlchemy models in `app/models/`
3. Create endpoint in `app/api/v1/[domain].py`
4. Include router in `app/api/v1/router.py`
5. Create migration if database changes
6. Add frontend API calls in `src/api/`
7. Create React Query hooks for data fetching

### Adding New Scraper

1. Create scraper class in `app/scrapers/[portal].py`
2. Implement URL parsing and data extraction
3. Map to Property schema
4. Add Celery task for periodic checks
5. Configure in settings (rate limits, selectors)

### Geographic Data

- Use WGS84 (SRID 4326) for all coordinates
- Property locations stored as PostGIS Geography POINT
- Frontend uses Leaflet for map visualization
- Color-code markers based on price, type, or custom filters

### Currency Handling

- Support USD and ARS via Currency enum
- Price per square meter calculated automatically
- Store all prices with currency type
- Historical exchange rates should be considered for ARS prices

## Celery Task Queue

- Worker: `celery -A app.tasks.celery_app worker --loglevel=info`
- Beat scheduler: `celery -A app.tasks.celery_app beat --loglevel=info`
- Redis as broker and result backend
- Scheduled tasks:
  - Periodic URL checks for price changes
  - Automatic material/labor cost updates
  - PDF report generation (WeasyPrint)
  - Price change notifications

## PDF Generation

- Use WeasyPrint (already in requirements.txt)
- Generate reports with property details, photos, analysis
- Include charts and maps in PDFs
- Store PDFs in `uploads/` directory

## Target Portals

**Supported Real Estate Portals:**
- Argenprop: https://www.argenprop.com.ar/
- Zonaprop: https://www.zonaprop.com.ar/
- Remax: https://www.remax.com.ar/
- MercadoLibre: https://inmuebles.mercadolibre.com.ar/
- BuscaInmueble: https://www.buscainmueble.com/ (future)

**Expected Data Extraction:**
- Property details (type, operation, surfaces)
- Pricing and currency
- Location (address, neighborhood, zone)
- Characteristics (bedrooms, bathrooms, parking, amenities)
- Agency and contact information
- Photo gallery
- Original URL for tracking
