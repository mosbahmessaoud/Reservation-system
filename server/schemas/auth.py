"""
Schemas for authentication (login, token).
"""
from .user import UserOut
from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: int
    role: str


class LoginRequest(BaseModel):
    phone_number: str
    password: str


class OTPSendRequest(BaseModel):
    phone_number: str


class OTPVerifyRequest(BaseModel):
    phone_number: str
    otp_code: str


class RegisterResponse(BaseModel):
    message: str
    user: UserOut
