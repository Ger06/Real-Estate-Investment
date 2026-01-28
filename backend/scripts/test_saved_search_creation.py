import sys
import os
import asyncio
from uuid import uuid4

# Add backend directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from app.schemas.saved_search import SavedSearchCreate
from app.models.saved_search import SavedSearch

def test_creation():
    print("Testing SavedSearch Creation Logic...")

    payload = {
        "name": "Test Remax Refinado",
        "portals": ["remax"],
        "operation_type": "VENTA",
        "city": "capital federal",
        "property_type": "DEPARTAMENTO",
        "auto_scrape": True,
        "neighborhoods": ["villa del parque"],
        "min_price": 200000.0,
        "max_price": 300000.0,
    }

    try:
        # 1. Test Pydantic Validation
        print("\nValidating schema...")
        search_in = SavedSearchCreate(**payload)
        print(f"✅ Schema valid. Neighborhoods: {search_in.neighborhoods}")

        # 2. Test Model Dump
        print("\nDumping model...")
        search_data = search_in.model_dump()
        print(f"Search Data: {search_data}")
        
        if search_data.get('neighborhoods') == ["villa del parque"]:
            print("✅ 'neighborhoods' present in model dump")
        else:
            print(f"❌ 'neighborhoods' MISSING or wrong in dump: {search_data.get('neighborhoods')}")

        # 3. Simulate DB Object Creation
        print("\nCreating DB Object...")
        # Note: We can't easily connect to the real DB without async setup, 
        # but we can verify the object initialization works
        new_search = SavedSearch(**search_data)
        
        print(f"DB Object Neighborhoods: {new_search.neighborhoods}")
        if new_search.neighborhoods == ["villa del parque"]:
             print("✅ DB Object has neighborhoods")
        else:
             print("❌ DB Object missing neighborhoods")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_creation()
