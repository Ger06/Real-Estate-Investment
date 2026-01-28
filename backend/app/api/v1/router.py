"""
API v1 Router
Aggregates all API endpoints
"""
from fastapi import APIRouter

from app.api.v1 import auth, properties, analytics, costs, investments, saved_searches, pending_properties, remax_cache


api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(costs.router, prefix="/costs", tags=["costs"])
api_router.include_router(investments.router, prefix="/investments", tags=["investments"])
api_router.include_router(saved_searches.router, prefix="/saved-searches", tags=["saved-searches"])
api_router.include_router(pending_properties.router, prefix="/pending-properties", tags=["pending-properties"])
api_router.include_router(remax_cache.router, prefix="/remax-cache", tags=["remax-cache"])
