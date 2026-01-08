"""
Script to create a test user
"""
import asyncio
from app.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash


async def create_test_user():
    """Create a test user"""
    async with AsyncSessionLocal() as db:
        # Check if user exists
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.email == "admin@test.com"))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print("✓ User admin@test.com already exists")
            return
        
        # Create new user
        user = User(
            email="admin@test.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Admin User",
            is_active=True,
            is_superuser=True
        )
        
        db.add(user)
        await db.commit()
        print("✓ Created user: admin@test.com")
        print("✓ Password: admin123")


if __name__ == "__main__":
    asyncio.run(create_test_user())
