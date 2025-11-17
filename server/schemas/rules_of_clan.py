"""
Committee schemas.
"""
from typing import Optional
from pydantic import BaseModel


class Update_Clan_Rules(BaseModel):
    general_rule: Optional[str] = None
    groom_supplies: Optional[str] = None
    rule_about_clothing: Optional[str] = None
    rule_about_kitchenware: Optional[str] = None
    rules_book_of_clan_pdf: Optional[str] = None


class Clan_Rules(BaseModel):
    general_rule: Optional[str] = None
    groom_supplies: Optional[str] = None
    rule_about_clothing: Optional[str] = None
    rule_about_kitchenware: Optional[str] = None
    rules_book_of_clan_pdf: Optional[str] = None
    clan_id: Optional[int]


class Clan_Rules_Create(Clan_Rules):
    pass


class Clan_Rules_Out(Clan_Rules):
    id: int

    class Config:
        from_attributes = True
