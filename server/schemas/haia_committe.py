"""
Committee schemas.
"""
from typing import Optional
from pydantic import BaseModel


class HaiaUpdate(BaseModel):
    name: Optional[str] = None
    county_id: Optional[int] = None


class HaiaBase(BaseModel):
    name: str
    county_id: int


class HaiaCreate(HaiaBase):
    pass


class HaiaOut(HaiaBase):
    id: int

    class Config:
        from_attributes = True
