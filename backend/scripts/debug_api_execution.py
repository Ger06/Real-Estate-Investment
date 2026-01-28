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
from app.models.saved_search import SavedSearch
from sqlalchemy import select
from uuid import UUID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_execution():
    print("--- Debugging API Execution Logic ---")
    
    # Target Search ID from user logs
    search_id_str = "d0de6e4f-ebaa-4e08-bb9c-5eb0b3425728"
    try:
        search_id = UUID(search_id_str)
    except ValueError:
        print(f"❌ Invalid UUID: {search_id_str}")
        return

    async with AsyncSessionLocal() as db:
        print(f"Fetching SavedSearch {search_id}...")
        stmt = select(SavedSearch).where(SavedSearch.id == search_id)
        result = await db.execute(stmt)
        search = result.scalar_one_or_none()
        
        if not search:
            print("❌ Search not found in DB!")
            return

        print(f"✅ Found Search: {search.name}")
        print(f"   Portals: {search.portals}")
        print(f"   Params: city={search.city}, neighborhoods={search.neighborhoods}, "
              f"min_price={search.min_price}, max_price={search.max_price}")

        print("\n--- Executing Search via MonitoringService ---")
        service = MonitoringService(db)
        results = await service.execute_search(search, max_properties=5)
        
        print("\n--- Execution Results ---")
        print(results)

if __name__ == "__main__":
    asyncio.run(debug_execution())
