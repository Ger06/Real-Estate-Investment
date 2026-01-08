"""
Construction cost and investment models
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, DateTime, Date, Enum, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class CostCategory(str, enum.Enum):
    """Cost category"""
    MATERIALS = "materials"
    LABOR = "labor"
    EQUIPMENT = "equipment"
    SERVICES = "services"
    PERMITS = "permits"
    OTHER = "other"


class Currency(str, enum.Enum):
    """Currency"""
    USD = "USD"
    ARS = "ARS"


class ConstructionCost(Base):
    """Construction cost item"""
    
    __tablename__ = "construction_costs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(Enum(CostCategory), nullable=False, index=True)
    item_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    unit = Column(String(50), nullable=False)  # m2, m3, kg, unit, etc.
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(Enum(Currency), nullable=False, default=Currency.ARS)
    supplier = Column(String(255), nullable=True)
    valid_from = Column(Date, nullable=False, default=date.today)
    valid_until = Column(Date, nullable=True)
    item_metadata = Column(JSONB, nullable=True)  # Additional flexible data (renamed from metadata)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    history = relationship("CostHistory", back_populates="cost", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_cost_search', 'category', 'item_name'),
        Index('idx_cost_validity', 'valid_from', 'valid_until'),
    )
    
    def __repr__(self) -> str:
        return f"<ConstructionCost {self.item_name}>"


class CostHistory(Base):
    """Historical tracking of cost changes"""
    
    __tablename__ = "cost_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cost_id = Column(UUID(as_uuid=True), ForeignKey("construction_costs.id"), nullable=False, index=True)
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(Enum(Currency), nullable=False)
    change_percentage = Column(Numeric(5, 2), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    cost = relationship("ConstructionCost", back_populates="history")
    
    __table_args__ = (
        Index('idx_cost_history_lookup', 'cost_id', 'recorded_at'),
    )
    
    def __repr__(self) -> str:
        return f"<CostHistory {self.cost_id} - {self.price}>"


class ProjectStatus(str, enum.Enum):
    """Investment project status"""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class InvestmentProject(Base):
    """Investment project tracking"""
    
    __tablename__ = "investment_projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Project details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Financial data
    purchase_price = Column(Numeric(12, 2), nullable=False)
    purchase_currency = Column(Enum(Currency), nullable=False, default=Currency.USD)
    renovation_budget = Column(Numeric(12, 2), nullable=True)
    actual_renovation_cost = Column(Numeric(12, 2), nullable=True)
    other_costs = Column(Numeric(12, 2), nullable=True)  # taxes, fees, etc.
    estimated_sale_price = Column(Numeric(12, 2), nullable=True)
    actual_sale_price = Column(Numeric(12, 2), nullable=True)
    
    # Calculations
    total_investment = Column(Numeric(12, 2), nullable=True)
    roi_percentage = Column(Numeric(5, 2), nullable=True)
    profit = Column(Numeric(12, 2), nullable=True)
    
    # Timeline
    start_date = Column(Date, nullable=True)
    estimated_completion_date = Column(Date, nullable=True)
    actual_completion_date = Column(Date, nullable=True)
    timeline_months = Column(Integer, nullable=True)
    
    # Status
    status = Column(Enum(ProjectStatus), nullable=False, default=ProjectStatus.PLANNING, index=True)
    
    # Additional data
    cost_breakdown = Column(JSONB, nullable=True)  # Detailed cost items
    milestones = Column(JSONB, nullable=True)  # Project milestones
    notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    property = relationship("Property", back_populates="investment_projects")
    user = relationship("User", back_populates="investment_projects")
    
    __table_args__ = (
        Index('idx_project_status', 'user_id', 'status'),
    )
    
    def __repr__(self) -> str:
        return f"<InvestmentProject {self.name}>"
