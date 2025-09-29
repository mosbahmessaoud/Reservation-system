"""
Clan model: Each clan belongs to a county, and has many relationships.
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from ..db import Base


class Clan(Base):
    __tablename__ = "clans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    county_id = Column(Integer, ForeignKey(
        "counties.id", ondelete="CASCADE"), nullable=False)

    # Relationships with lazy loading
    county = relationship("County", back_populates="clans", lazy="select")
    users = relationship("User", back_populates="clan",
                         lazy="select")
    halls = relationship("Hall", back_populates="clan",
                         cascade="all, delete-orphan", passive_deletes=True, lazy="select")
    clanrules = relationship(
        "ClanRules", back_populates="clan",    cascade="all, delete-orphan", passive_deletes=True, uselist=False, lazy="select")
    food_menus = relationship(
        "FoodMenu", back_populates="clan",          cascade="all, delete-orphan",  # SQLAlchemy side
        passive_deletes=True, lazy="select")
    settings = relationship("ClanSettings", back_populates="clan",
                            uselist=False, cascade="all, delete-orphan", passive_deletes=True, lazy="select")
    reservations = relationship(
        "Reservation", back_populates="clan", lazy="select")
