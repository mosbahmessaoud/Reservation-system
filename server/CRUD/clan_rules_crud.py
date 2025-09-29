from sqlalchemy.orm import Session
from typing import List, Optional

from server.models.clan_rules import ClanRules
from server.schemas.clan_rules_schema import ClanRulesCreate, ClanRulesUpdate


def get_by_id(db: Session, rule_id: int) -> Optional[ClanRules]:
    """Get clan rules by ID"""
    return db.query(ClanRules).filter(ClanRules.id == rule_id).first()


def get_by_clan_id(db: Session, clan_id: int) -> Optional[ClanRules]:
    """Get clan rules by clan_id"""
    return db.query(ClanRules).filter(ClanRules.clan_id == clan_id).first()


def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[ClanRules]:
    """Get all clan rules with pagination"""
    return db.query(ClanRules).offset(skip).limit(limit).all()


def create(db: Session, rules_data: ClanRulesCreate) -> ClanRules:
    """Create new clan rules"""
    db_rules = ClanRules(
        clan_id=rules_data.clan_id,
        general_rule=rules_data.general_rule,
        groom_supplies=rules_data.groom_supplies,
        rule_about_clothing=rules_data.rule_about_clothing,
        rule_about_kitchenware=rules_data.rule_about_kitchenware
    )
    db.add(db_rules)
    db.commit()
    db.refresh(db_rules)
    return db_rules


def update(db: Session, rule_id: int, rules_data: ClanRulesUpdate) -> Optional[ClanRules]:
    """Update clan rules"""
    db_obj = get_by_id(db, rule_id)
    if not db_obj:
        return None

    update_data = rules_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete(db: Session, rule_id: int) -> bool:
    """Delete clan rules"""
    db_obj = get_by_id(db, rule_id)
    if not db_obj:
        return False

    db.delete(db_obj)
    db.commit()
    return True
