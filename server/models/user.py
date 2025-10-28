"""
User model: Super Admin, Clan Admin, Groom.
"""
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Date, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from ..db import Base


class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    clan_admin = "clan_admin"
    groom = "groom"


class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"  # Changed from "not_active" to "inactive"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)

    # Common names
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    father_name = Column(String, nullable=False)
    grandfather_name = Column(String, nullable=False)

    # Personal info
    birth_date = Column(Date)
    birth_address = Column(String)
    home_address = Column(String)

    # phone number verefication
    phone_verified = Column(Boolean, default=False)

    otp_code = Column(String, nullable=True)
    otp_expiration = Column(DateTime, nullable=True)

    # Phone number update on updating the number case
    temp_phone_number = Column(String, nullable=True)
    temp_phone_otp_code = Column(String, nullable=True)
    temp_phone_otp_expires_at = Column(DateTime, nullable=True)

    # Relation to clan (nullable for super admin)
    clan_id = Column(Integer, ForeignKey("clans.id"), nullable=True)
    clan = relationship("Clan", back_populates="users", lazy="select")

    county_id = Column(Integer, ForeignKey("counties.id"), nullable=True)
    county = relationship("County",
                          back_populates="users", lazy="select")

    # Groom-specific fields
    guardian_name = Column(String, nullable=True)
    guardian_phone = Column(String, nullable=True)
    guardian_relation = Column(String, nullable=True)
    # Personal info
    guardian_birth_date = Column(Date)
    guardian_birth_address = Column(String)
    guardian_home_address = Column(String)

    # New columns
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(Enum(UserStatus),
                    default=UserStatus.active, nullable=False)

    # Relationships
    reservations = relationship(
        "Reservation", back_populates="groom", lazy="select",     cascade="all")

    def is_super_admin(self):
        return self.role == UserRole.super_admin

    def is_clan_admin(self):
        return self.role == UserRole.clan_admin

    def is_groom(self):
        return self.role == UserRole.groom
