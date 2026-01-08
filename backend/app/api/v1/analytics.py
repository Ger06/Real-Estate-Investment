"""
Analytics API endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/market-overview")
async def get_market_overview():
    """Get market overview analytics"""
    return {"message": "Market overview - to be implemented"}


@router.get("/price-trends")
async def get_price_trends():
    """Get price trends"""
    return {"message": "Price trends - to be implemented"}
