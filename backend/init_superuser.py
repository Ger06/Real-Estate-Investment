"""
Script to initialize the first superuser from configuration
"""
import asyncio
from app.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import settings


async def init_superuser():
    """Create initial superuser from config settings"""
    async with AsyncSessionLocal() as db:
        # Check if superuser already exists
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"✓ Superuser {settings.FIRST_SUPERUSER_EMAIL} already exists")
            return

        # Create superuser
        user = User(
            email=settings.FIRST_SUPERUSER_EMAIL,
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            full_name="Administrator",
            is_active=True,
            is_superuser=True
        )

        db.add(user)
        await db.commit()
        print(f"✓ Created superuser: {settings.FIRST_SUPERUSER_EMAIL}")
        print(f"✓ Password: {settings.FIRST_SUPERUSER_PASSWORD}")
        print("\n⚠️  IMPORTANT: Change these credentials in production!")


if __name__ == "__main__":
    asyncio.run(init_superuser())
