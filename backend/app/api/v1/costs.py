"""
Construction Costs API endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_costs():
    """List all construction costs"""
    return {"message": "Costs endpoint - to be implemented"}


@router.post("/")
async def create_cost():
    """Create a new cost item"""
    return {"message": "Create cost - to be implemented"}
