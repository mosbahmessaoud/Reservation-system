# """
# Reservation schemas.
# """
# from pydantic import BaseModel
# from typing import Optional
# from datetime import date, datetime

# from server.schemas.clan import ClanOut
# from server.schemas.county import CountyOut

# class ReservationCreateResponse(BaseModel):
#     message: str
#     reservation_id: int
#     pdf_url: str 
    
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
#     pdf_url: Optional[str] = None  # New field for generated PDF link


# class ReservationCreate(ReservationBase):
#     pass

# class ReservationOut(BaseModel):
#     # Reservation fields
#     id: int
#     groom_id: int
#     clan_id: int
#     county_id: int  # Add this field

#     date1: date
#     date2: Optional[date] = None
#     date2_bool: bool = False
#     allow_others: bool = False
#     join_to_mass_wedding: bool = False
#     status: str
#     created_at: datetime
#     expires_at: Optional[datetime] = None
#     hall_id: Optional[int] = None
#     haia_committee_id: Optional[int] = None
#     madaeh_committee_id: Optional[int] = None
#     pdf_url: Optional[str] = None

#     # User fields - make them optional to avoid validation errors
#     # county: Optional[int] = None
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

#     class Config:
#         from_attributes = True
