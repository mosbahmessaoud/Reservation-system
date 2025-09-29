"""
Committee schemas.
"""
from typing import Optional
from pydantic import BaseModel


class MadaihUpdate(BaseModel):
    name: Optional[str] = None
    county_id: Optional[int] = None


class MadaihBase(BaseModel):
    name: str
    county_id: int


class MadaihCreate(MadaihBase):
    pass


class MadaihOut(MadaihBase):
    id: int

    class Config:
        from_attributes = True
