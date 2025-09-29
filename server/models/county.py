"""
County model: Each county has many clans.
"""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from ..db import Base


class County(Base):
    __tablename__ = "counties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    clans = relationship("Clan", back_populates="county",
                         cascade="all, delete")
    users = relationship("User", back_populates="county"
                         )

    haia_committee = relationship(
        "HaiaCommittee", back_populates="county", cascade="all, delete")
    madaeh_committees = relationship(
        "MadaehCommittee", back_populates="county", cascade="all, delete")
    reservations = relationship("Reservation", back_populates="county", lazy="select")
