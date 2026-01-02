"""
Clan settings schemas.
"""
from decimal import Decimal
from token import OP
from pydantic import BaseModel
from typing import Optional


class ClanSettingsBase(BaseModel):
    max_grooms_per_date: Optional[int]
    years_max_reserv_GroomFromOutClan: Optional[int]
    years_max_reserv_GrooomFromOriginClan: Optional[int]
    allow_two_day_reservations: Optional[bool]
    validation_deadline_days: Optional[int]
    allowed_months_single_day: Optional[str]
    allowed_months_two_day: Optional[str]
    calendar_years_ahead: Optional[int]
    days_to_accept_invites: Optional[str]
    accept_invites_times: Optional[str]
    allow_cross_clan_reservations: Optional[bool]
    payment_should_pay: Decimal = Decimal("0.00")  # Set default here


class ClanSettingUpdatePayment(BaseModel):
    payment_should_pay: Optional[Decimal]


class ClanSettingsCreate(ClanSettingsBase):
    clan_id: int  # Used only when creating a new settings row


class ClanSettingsUpdate(ClanSettingsBase):
    # No clan_id required here; it's taken from the path or current user
    pass


class ClanSettingsOut(ClanSettingsBase):
    id: int
    clan_id: int

    class Config:
        from_attributes = True
