"""
User schemas.
"""
from enum import Enum
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import date, datetime


from server.models.user import UserStatus, UserRole


class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    # banned = "banned"  # optional

# Request model for status update


class StatusUpdateRequest(BaseModel):
    status: Literal["active", "inactive"]


class UpdateGroomRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    father_name: Optional[str] = None
    grandfather_name: Optional[str] = None
    birth_date: Optional[date] = None  # Changed from str to date
    birth_address: Optional[str] = None
    home_address: Optional[str] = None
    phone_number: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_home_address: Optional[str] = None
    guardian_birth_address: Optional[str] = None
    guardian_birth_date: Optional[date] = None  # Changed from str to date
    guardian_relation: Optional[str] = None
    status: Optional[UserStatus] = None


class UserBase(BaseModel):
    phone_number: str
    first_name: str
    last_name: str
    father_name: str
    grandfather_name: str
    birth_date: Optional[date] = None
    birth_address: Optional[str] = None
    home_address: Optional[str] = None
    clan_id: Optional[int] = None
    county_id: Optional[int] = None


class UserCreate(UserBase):
    password: str
    role: UserRole  # Changed from str to UserRole enum
    # Guardian info only for grooms
    guardian_name: Optional[str] = None
    guardian_home_address: Optional[str] = None
    guardian_birth_address: Optional[str] = None
    guardian_birth_date: Optional[date] = None
    guardian_phone: Optional[str] = None
    guardian_relation: Optional[str] = None
    status: Optional[UserStatus] = UserStatus.active  # Set default value


class UserUpdate(BaseModel):
    """
    Schema for updating a user (clan admin or groom).
    All fields optional for partial updates.
    """
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    father_name: Optional[str] = None
    grandfather_name: Optional[str] = None
    birth_date: Optional[date] = None
    birth_address: Optional[str] = None
    home_address: Optional[str] = None
    clan_id: Optional[int] = None
    county_id: Optional[int] = None
    status: Optional[UserStatus] = None

    # Guardian info only for grooms
    guardian_name: Optional[str] = None
    guardian_home_address: Optional[str] = None
    guardian_birth_address: Optional[str] = None
    guardian_birth_date: Optional[date] = None
    guardian_phone: Optional[str] = None
    guardian_relation: Optional[str] = None


class UpdateUserStatusRequest(BaseModel):
    """Schema specifically for status updates"""
    status: UserStatus


class DeleteResponse(BaseModel):
    message: str


class UserOut(UserBase):
    id: int
    role: UserRole  # Changed from str to UserRole enum
    phone_verified: bool = False
    created_at: datetime  # Added created_at field
    status: UserStatus  # Made required, not Optional

    # Guardian info only for grooms
    guardian_name: Optional[str] = None
    guardian_home_address: Optional[str] = None
    guardian_birth_address: Optional[str] = None
    guardian_birth_date: Optional[date] = None
    guardian_phone: Optional[str] = None
    guardian_relation: Optional[str] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for paginated user list responses"""
    users: list[UserOut]
    total: int
    page: int
    per_page: int


class GroomStatusUpdateResponse(BaseModel):
    """Response schema for groom status updates"""
    message: str
    user_id: int
    new_status: UserStatus
