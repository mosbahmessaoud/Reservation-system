"""
ClanSettings model: editable by clan admin, controls reservation rules.
"""
from sqlalchemy import Column, DateTime, Integer, Boolean, Numeric, String, ForeignKey, ARRAY
from sqlalchemy.orm import relationship

from ..db import Base


class ClanSettings(Base):
    __tablename__ = "clan_settings"

    id = Column(Integer, primary_key=True, index=True)
    clan_id = Column(Integer, ForeignKey(
        "clans.id", ondelete="CASCADE"), unique=True, nullable=False)
    allow_cross_clan_reservations = Column(
        Boolean, default=False)

    max_grooms_per_date = Column(Integer, default=3)
    allow_two_day_reservations = Column(Boolean, default=False)
    validation_deadline_days = Column(Integer, default=10)
    # November–April (comma-separated months)
    allowed_months_single_day = Column(String, default="11,12,1,2,3,4")
    allowed_months_two_day = Column(
        String, default="5,6,7,8,9,10")  # May–October
    calendar_years_ahead = Column(Integer, default=3)
  # Days and times when invites are accepted
    days_to_accept_invites = Column(String, nullable=True)
    accept_invites_times = Column(String, nullable=True)

    payment_should_pay = Column(
        Numeric(15, 2), nullable=True, default=0.00, server_default='0.00')
    # mew columns
    years_max_reserv_GroomFromOutClan = Column(Integer, default=3)
    years_max_reserv_GrooomFromOriginClan = Column(Integer, default=1)

    clan = relationship("Clan", back_populates="settings")
