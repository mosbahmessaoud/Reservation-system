# server\models\reservation.py
"""
Reservation model: Each reservation is for a groom, in a clan, for 1 or 2 consecutive days.
"""
import re
from sqlalchemy import Column, Integer, Date, Boolean, ForeignKey, Null, String, Enum, DateTime, null, true
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..db import Base


class ReservationSpecialStatus(str, enum.Enum):
    validated = "validated"
    cancelled = "cancelled"


class ReservationSpecial(Base):
    __tablename__ = "reservations_special"

    id = Column(Integer, primary_key=True, index=True)
    clan_id = Column(Integer, ForeignKey("clans.id"), nullable=False)
    county_id = Column(Integer, ForeignKey("counties.id"), nullable=False)
    reserv_name = Column(String, nullable=False)
    reserv_desctiption = Column(String, nullable=True)

    date = Column(Date, nullable=False)
    status = Column(Enum(ReservationSpecialStatus),
                    default=ReservationSpecialStatus.validated, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    clan = relationship(
        "Clan", back_populates="reservations_special", lazy="select")
    county = relationship(
        "County", back_populates="reservations_special", lazy="select")
