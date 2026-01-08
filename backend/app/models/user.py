"""
User model for authentication and authorization
"""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """User model"""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - Temporarily disabled due to circular reference issues
    # properties = relationship("Property", back_populates="created_by_user", foreign_keys="[Property.created_by]")
    # visits = relationship("PropertyVisit", back_populates="user")
    # investment_projects = relationship("InvestmentProject", back_populates="user")
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
