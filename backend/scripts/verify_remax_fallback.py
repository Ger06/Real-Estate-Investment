import sys
import os
import asyncio
import logging

# Add backend directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from app.database import get_db, AsyncSessionLocal
from app.services.monitoring import MonitoringService
from app.models.saved_search import SavedSearch, PropertyType, OperationType, Currency
from uuid import UUID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_fallback_logic():
    print("--- Verifying Remax Fallback Logic (PH / Villa Crespo) ---")
    
    # Create a dummy search object in memory
    search = SavedSearch(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        name="Test Fallback",
        portals=["remax"],
        property_type=PropertyType.PH,
        operation_type=OperationType.VENTA,
        neighborhoods=["Villa Crespo"],
        min_price=50000.0,
        max_price=300000.0,
        currency=Currency.USD
    )

    async with AsyncSessionLocal() as db:
        print("\n--- Executing Search via MonitoringService ---")
        service = MonitoringService(db)
        
        # This should trigger:
        # 1. URL generation -> departamentos-en-venta-en-ciudad-de-buenos-aires
        # 2. Scraping hundreds of results
        # 3. Filtering down to only Villa Crespo + PH
        
        print("Starting search... (this might take a moment to filter)")
        results = await service.execute_search(search, max_properties=100) # Request more to ensure we find some matches
        
        print("\n--- Execution Results ---")
        print(results)
        
        if results['new_properties'] > 0:
            print(f"✅ FOUND {results['new_properties']} properties via fallback!")
        else:
            print("⚠️ Found 0 properties. Check logs to see if filtering was too strict.")

if __name__ == "__main__":
    asyncio.run(verify_fallback_logic())
