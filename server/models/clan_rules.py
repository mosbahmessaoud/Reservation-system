"""
Hall model: Each hall belongs to a clan.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from ..db import Base


class ClanRules(Base):
    __tablename__ = "clan_rules"

    id = Column(Integer, primary_key=True, index=True)
    general_rule = Column(Text, nullable=True)
    groom_supplies = Column(Text, nullable=True)
    rule_about_clothing = Column(Text, nullable=True)
    rule_about_kitchenware = Column(Text, nullable=True)
    rules_book_of_clan_pdf = Column(String, nullable=True)

    clan_id = Column(Integer, ForeignKey(
        "clans.id", ondelete="CASCADE"), nullable=False)

    clan = relationship("Clan", back_populates="clanrules")
