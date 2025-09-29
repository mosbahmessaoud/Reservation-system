# """
# Reservation model: Each reservation is for a groom, in a clan, for 1 or 2 consecutive days.
# """
# from sqlalchemy import Column, Integer, Date, Boolean, ForeignKey, Null, String, Enum, DateTime, null, true
# from sqlalchemy.orm import relationship
# from datetime import datetime
# import enum

# from ..db import Base


# class ReservationStatus(str, enum.Enum):
#     pending_validation = "pending_validation"
#     validated = "validated"
#     cancelled = "cancelled"


# class Reservation(Base):
#     __tablename__ = "reservations"

#     id = Column(Integer, primary_key=True, index=True)
#     groom_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     clan_id = Column(Integer, ForeignKey("clans.id"), nullable=False)
#     county_id = Column(Integer, ForeignKey("counties.id"),
#                        nullable=True)  # New column

#     date1 = Column(Date, nullable=False)
#     date2 = Column(Date, default=None, nullable=True)
#     date2_bool = Column(Boolean, default=False, nullable=True)

#     allow_others = Column(Boolean, default=False, nullable=False)
#     join_to_mass_wedding = Column(Boolean, default=False, nullable=False)
#     status = Column(Enum(ReservationStatus),
#                     default=ReservationStatus.pending_validation, nullable=False)
#     created_at = Column(DateTime, default=datetime.utcnow)
#     expires_at = Column(DateTime, nullable=True)

#     # Selections (nullable until finalized)
#     hall_id = Column(Integer, ForeignKey(
#         "halls_table.id"), nullable=True)
#     haia_committee_id = Column(Integer, ForeignKey(
#         "haia_committee.id"), nullable=True)
#     madaeh_committee_id = Column(Integer, ForeignKey(
#         "madaeh_committees.id"), nullable=True)

#     pdf_url = Column(String, nullable=True)  # New field for generated PDF link

#     groom = relationship("User", back_populates="reservations")
#     clan = relationship("Clan", back_populates="reservations")

