"""
Investment Projects API endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_investments():
    """List all investment projects"""
    return {"message": "Investments endpoint - to be implemented"}


@router.post("/")
async def create_investment():
    """Create a new investment project"""
    return {"message": "Create investment - to be implemented"}
