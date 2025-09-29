"""
Food Models for Wedding Food Menu System
Path: server/models/food.py
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from ..db import Base
from sqlalchemy.dialects.postgresql import JSON


class FoodMenu(Base):

    __tablename__ = "food_menus"

    id = Column(Integer, primary_key=True, index=True)
    # "Traditional", "Modern", "Mixed"
    food_type = Column(String(50), nullable=False)
    number_of_visitors = Column(Integer, nullable=False)  # 100, 150, 200, etc.
    # JSON string with menu items list
    # menu_details = Column(Text, nullable=False)
    menu_details = Column(JSON, nullable=False)  # Store as JSON list directly

    clan_id = Column(Integer, ForeignKey(
        "clans.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    clan = relationship("Clan", back_populates="food_menus")
