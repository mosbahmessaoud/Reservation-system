# # server\schemas\reservation.py
# from decimal import Decimal
# from pydantic import BaseModel
# from datetime import datetime, date
# from typing import Literal, Optional
# from enum import Enum


# class ReservationStatus(str, Enum):
#     pending_validation = "pending_validation"
#     validated = "validated"
#     cancelled = "cancelled"


# class ReservationBase(BaseModel):
#     date1: date
#     date2: Optional[date] = None
#     date2_bool: Optional[bool] = False
#     allow_others: Optional[bool] = False
#     join_to_mass_wedding: Optional[bool] = False
#     clan_id: int
#     hall_id: Optional[int] = None
#     haia_committee_id: Optional[int] = None
#     madaeh_committee_id: Optional[int] = None
#     pdf_url: Optional[str] = None


# class ReservationCreate(ReservationBase):
#     pass


# class ReservationOut(BaseModel):
#     # Core reservation fields
#     id: int
#     groom_id: int
#     clan_id: int
#     hall_id: Optional[int] = None
#     county_id: int

#     # Dates
#     date1: date
#     date2: Optional[date] = None
#     date2_bool: Optional[bool] = None

#     # Wedding type settings
#     join_to_mass_wedding: bool
#     allow_others: bool

#     # Status and timing
#     status: Optional[ReservationStatus] = None
#     payment_valid: Optional[bool] = None
#     created_at: Optional[datetime] = None

#     # Committee assignments
#     haia_committee_id: Optional[int] = None
#     madaeh_committee_id: Optional[int] = None

#     # Groom personal information
#     first_name: Optional[str] = None
#     last_name: Optional[str] = None
#     guardian_name: Optional[str] = None
#     father_name: Optional[str] = None
#     grandfather_name: Optional[str] = None
#     birth_date: Optional[date] = None
#     birth_address: Optional[str] = None
#     home_address: Optional[str] = None
#     phone_number: Optional[str] = None
#     guardian_phone: Optional[str] = None

#     # PDF and response info
#     pdf_url: Optional[str] = None
#     message: Optional[str] = None
#     reservation_id: Optional[int] = None

#     class Config:
#         from_attributes = True  # For SQLAlchemy ORM compatibility

#     # Alternative minimal response structure for the endpoint return
#     @classmethod
#     def create_response(cls, reservation_id: int, pdf_url: str):
#         """Create a minimal response matching the endpoint return"""
#         return {
#             "message": "Reservation created successfully",
#             "reservation_id": reservation_id,
#             "pdf_url": pdf_url
#         }


# class ReservationCreateResponse(BaseModel):
#     message: Optional[str] = None
#     reservation_id: int
#     pdf_url: Optional[str] = None
