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

async def verify_deep_fallback():
    print("--- Verifying Remax Deep Scrape Fallback (PH / Villa Crespo) ---")
    
    # Create a dummy search object in memory
    search = SavedSearch(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        name="Test Deep Fallback",
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
        
        # This should:
        # 1. Generate fallback URL
        # 2. Scrape Page 1 (Likely 0 results for VC PH in top 24 of CABA)
        # 3. NOT Stop being 0 results
        # 4. Scrape Page 2... 3... until it finds something or max pages
        
        print("Starting deep search... (This will take time as it scans multiple pages)")
        # Limit max_properties but ensure we scan enough pages implicitly via scraper logic
        results = await service.execute_search(search, max_properties=20) 
        
        print("\n--- Execution Results ---")
        print(results)
        
        if results['new_properties'] > 0:
            print(f"✅ FOUND {results['new_properties']} properties via deep fallback!")
        else:
            print("⚠️ Found 0 properties. Either very rare or deep scrape failed to paginate.")

if __name__ == "__main__":
    asyncio.run(verify_deep_fallback())
