"""
Two types of committees: CeremonyCommittee (هيئة) and MadaehCommittee (مدائح).
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from ..db import Base


class HaiaCommittee(Base):
    __tablename__ = "haia_committee"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    county_id = Column(Integer, ForeignKey(
        "counties.id", ondelete="CASCADE"), nullable=False)

    county = relationship("County", back_populates="haia_committee")
    reservations = relationship(
        "Reservation", back_populates="haia_committee", lazy="select")


class MadaehCommittee(Base):
    __tablename__ = "madaeh_committees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    county_id = Column(Integer, ForeignKey(
        "counties.id", ondelete="CASCADE"), nullable=False)

    county = relationship("County", back_populates="madaeh_committees")
    reservations = relationship(
        "Reservation", back_populates="madaeh_committee", lazy="select")
