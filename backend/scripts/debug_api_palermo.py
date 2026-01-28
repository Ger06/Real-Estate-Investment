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

async def debug_execution_palermo():
    print("--- Debugging API Execution Logic (Palermo Control) ---")
    
    # Create a dummy search object in memory
    search = SavedSearch(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        name="Test Palermo",
        portals=["remax"],
        property_type=PropertyType.DEPARTAMENTO,
        operation_type=OperationType.VENTA,
        neighborhoods=["palermo"],
        min_price=100000.0,
        max_price=300000.0,
        currency=Currency.USD
    )

    async with AsyncSessionLocal() as db:
        print("\n--- Executing Search via MonitoringService ---")
        service = MonitoringService(db)
        
        # We need to bypass the DB fetch in execute_search if we pass the object directly?
        # execute_search takes a SavedSearch object.
        results = await service.execute_search(search, max_properties=5)
        
        print("\n--- Execution Results ---")
        print(results)

if __name__ == "__main__":
    asyncio.run(debug_execution_palermo())
