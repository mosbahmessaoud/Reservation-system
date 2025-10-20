# server\schemas\reservations_special.py
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from enum import Enum


class ReservationSpecialStatus(str, Enum):
    validated = "validated"
    cancelled = "cancelled"


class ReservationSpecialBase(BaseModel):
    full_name: Optional[str] = None
    home_address: Optional[str] = None
    phone_number: Optional[str] = None
    reserv_name: Optional[str] = None
    reserv_desctiption: Optional[str] = None
    date: date


class ReservationSpecialCreate(ReservationSpecialBase):
    pass


class ReservationSpecialOut(BaseModel):
    id: int
    clan_id: int
    county_id: int
    full_name: Optional[str] = None
    home_address: Optional[str] = None
    phone_number: Optional[str] = None
    reserv_name: Optional[str] = None
    reserv_desctiption: Optional[str] = None
    date: date
    status: ReservationSpecialStatus
    created_at: datetime

    class Config:
        orm_mode = True
