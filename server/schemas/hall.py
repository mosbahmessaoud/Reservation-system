"""
Hall schemas.
"""
from pydantic import BaseModel


class HallBase(BaseModel):
    name: str
    capacity: int
    clan_id: int


class HallCreate(HallBase):
    pass


class HallOut(HallBase):
    id: int

    class Config:
        from_attributes = True
