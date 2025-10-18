# server\schemas\reservations_special.py
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from enum import Enum

from server.models.reservation_clan_admin import ReservationSpecialStatus


class ReservationSpecialBase(BaseModel):
    reserv_name: str
    reserv_desctiption: Optional[str] = None
    date: date


class ReservationSpecialCreate(ReservationSpecialBase):
    pass


class ReservationSpecialOut(BaseModel):
    id: int
    clan_id: int
    county_id: int
    reserv_name: str
    reserv_desctiption: Optional[str] = None
    date: date
    status: ReservationSpecialStatus
    created_at: datetime

    class Config:
        orm_mode = True
