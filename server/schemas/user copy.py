# """
# User schemas.
# """
# from pydantic import BaseModel
# from typing import Optional
# from datetime import date

# from server.models.user import UserStatus


# class UpdateGroomRequest(BaseModel):
#     first_name: Optional[str] = None
#     last_name: Optional[str] = None
#     father_name: Optional[str] = None
#     grandfather_name: Optional[str] = None
#     birth_date: Optional[str] = None
#     birth_address: Optional[str] = None
#     home_address: Optional[str] = None
#     phone_number: Optional[str] = None
#     guardian_name: Optional[str] = None
#     guardian_phone: Optional[str] = None
#     guardian_home_address: Optional[str] = None
#     guardian_birth_address: Optional[str] = None
#     guardian_birth_date: Optional[str] = None
#     guardian_relation: Optional[str] = None
#     status: Optional[UserStatus] = None


# class UserBase(BaseModel):
#     phone_number: str
#     first_name: str
#     last_name: str
#     father_name: str
#     grandfather_name: str
#     birth_date: Optional[date]
#     birth_address: Optional[str]
#     home_address: Optional[str]
#     clan_id: Optional[int]
#     county_id: Optional[int]


# class UserCreate(UserBase):
#     password: str
#     role: str
#     # Guardian info only for grooms
#     guardian_name: Optional[str] = None
#     guardian_home_address: Optional[str] = None
#     guardian_birth_address: Optional[str] = None
#     guardian_birth_date: Optional[date] = None
#     guardian_phone: Optional[str] = None
#     guardian_relation: Optional[str] = None
#     status: Optional[UserStatus] = None


# class UserUpdate(BaseModel):
#     """
#     Schema for updating a user (clan admin or groom).
#     All fields optional for partial updates.
#     """
#     # phone_number: Optional[str] = None
#     password: Optional[str] = None
#     first_name: Optional[str] = None
#     last_name: Optional[str] = None
#     father_name: Optional[str] = None
#     grandfather_name: Optional[str] = None
#     birth_date: Optional[date] = None
#     birth_address: Optional[str] = None
#     home_address: Optional[str] = None
#     clan_id: Optional[int] = None
#     county_id: Optional[int] = None
#     status: Optional[UserStatus] = None

#     # Guardian info (still optional for grooms only)

#     # Guardian info only for grooms
#     guardian_name: Optional[str] = None
#     guardian_home_address: Optional[str] = None
#     guardian_birth_address: Optional[str] = None
#     guardian_birth_date: Optional[date] = None
#     guardian_phone: Optional[str] = None
#     guardian_relation: Optional[str] = None


# class DeleteResponse(BaseModel):
#     message: str


# class UserOut(UserBase):
#     id: int
#     role: str
#     phone_verified: bool = False
#     # Guardian info only for grooms
#     guardian_name: Optional[str] = None
#     guardian_home_address: Optional[str] = None
#     guardian_birth_address: Optional[str] = None
#     guardian_birth_date: Optional[date] = None
#     guardian_phone: Optional[str] = None
#     guardian_relation: Optional[str] = None
#     status: Optional[UserStatus] = None

#     class Config:
#         from_attributes = True
