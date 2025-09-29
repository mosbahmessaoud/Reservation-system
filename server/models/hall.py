"""
Hall model: Each hall belongs to a clan.
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from ..db import Base


class Hall(Base):
    __tablename__ = "halls_table"

    id = Column(Integer, primary_key=True, index=True)
    capacity = Column(Integer, nullable=True)
    name = Column(String, nullable=False)
    clan_id = Column(Integer, ForeignKey(
        "clans.id", ondelete="CASCADE"), nullable=False)

    clan = relationship("Clan", back_populates="halls")
    reservations = relationship(
        "Reservation", back_populates="hall", lazy="select")
