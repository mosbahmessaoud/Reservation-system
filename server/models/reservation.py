# server\models\reservation.py
"""
Reservation model: Each reservation is for a groom, in a clan, for 1 or 2 consecutive days.
"""
from sqlalchemy import Column, Integer, Date, Boolean, ForeignKey, Null, String, Enum, DateTime, null, true
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..db import Base


class ReservationStatus(str, enum.Enum):
    pending_validation = "pending_validation"
    validated = "validated"
    cancelled = "cancelled"


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    groom_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    clan_id = Column(Integer, ForeignKey("clans.id"), nullable=False)
    county_id = Column(Integer, ForeignKey("counties.id"), nullable=False)

    date1 = Column(Date, nullable=False)
    date2 = Column(Date, default=None, nullable=True)
    date2_bool = Column(Boolean, default=False, nullable=True)

    allow_others = Column(Boolean, default=False, nullable=False)
    join_to_mass_wedding = Column(Boolean, default=False, nullable=False)
    status = Column(Enum(ReservationStatus),
                    default=ReservationStatus.pending_validation, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    payment_valid = Column(Boolean, default=False, nullable=True)  # added new

    # Selections (nullable until finalized)
    hall_id = Column(Integer, ForeignKey("halls_table.id"), nullable=True)
    haia_committee_id = Column(Integer, ForeignKey(
        "haia_committee.id"), nullable=True)
    madaeh_committee_id = Column(Integer, ForeignKey(
        "madaeh_committees.id"), nullable=True)

    # PDF and personal information fields
    pdf_url = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    father_name = Column(String, nullable=True)
    grandfather_name = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)
    birth_address = Column(String, nullable=True)
    home_address = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)

    guardian_name = Column(String, nullable=True)
    guardian_phone = Column(String, nullable=True)
    guardian_home_address = Column(String, nullable=True)
    guardian_birth_address = Column(String, nullable=True)
    guardian_birth_date = Column(Date, nullable=True)

    # Relationships
    groom = relationship("User", back_populates="reservations", lazy="select")
    clan = relationship("Clan", back_populates="reservations", lazy="select")
    county = relationship(
        "County", back_populates="reservations", lazy="select")
    hall = relationship("Hall", back_populates="reservations", lazy="select")
    haia_committee = relationship(
        "HaiaCommittee", back_populates="reservations", lazy="select")
    madaeh_committee = relationship(
        "MadaehCommittee", back_populates="reservations", lazy="select")
 