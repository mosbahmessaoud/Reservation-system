from pydantic import BaseModel
from typing import Optional


class ClanRulesBase(BaseModel):
    general_rule: Optional[str] = None
    groom_supplies: Optional[str] = None
    rule_about_clothing: Optional[str] = None
    rule_about_kitchenware: Optional[str] = None
    rules_book_of_clan_pdf: Optional[str] = None


class ClanRulesCreate(ClanRulesBase):
    clan_id: int


class ClanRulesUpdate(ClanRulesBase):
    pass


class ClanRulesResponse(ClanRulesBase):
    id: int
    clan_id: int

    class Config:
        from_attributes = True
