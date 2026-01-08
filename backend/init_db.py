"""
Script to initialize the database with all tables.
This bypasses Alembic and uses SQLAlchemy's create_all() method.
"""
import asyncio
from app.database import engine, Base
from app.models.user import User
from app.models.property import Property, PropertyImage, PriceHistory, PropertyVisit
from app.models.cost import ConstructionCost, CostHistory, InvestmentProject


async def init_db():
    """Create all tables in the database"""
    async with engine.begin() as conn:
        # Drop all tables first (clean slate)
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("✓ Database initialized successfully!")
    print("✓ All tables created")


if __name__ == "__main__":
    asyncio.run(init_db())
