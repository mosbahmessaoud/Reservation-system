"""
County schemas.
"""
from typing import Optional
from pydantic import BaseModel


class CountyUpdate(BaseModel):
    name: Optional[str] = None
    # county_id: Optional[int] = None


class CountyBase(BaseModel):
    name: str


class CountyCreate(CountyBase):
    pass


class CountyOut(CountyBase):
    id: int

    class Config:
        orm_mode = True
        # from_attributes = True
