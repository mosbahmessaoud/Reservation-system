"""
Clan schemas.
"""
from pydantic import BaseModel
from typing import Optional


class ClanUpdate(BaseModel):
    name: Optional[str] = None
    county_id: Optional[int] = None


class ClanBase(BaseModel):
    name: str
    county_id: int


class ClanCreate(ClanBase):
    pass


class ClanOut(ClanBase):
    id: int
    name: str
    county_id: int

    class Config:
        from_attributes = True
