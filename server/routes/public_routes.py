"""
Public routes for getting clans by county and halls by clan.
These routes are used during reservation creation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from server.schemas.county import CountyOut

from ..auth_utils import get_db
from ..models.clan import Clan
from ..models.hall import Hall
from ..models.county import County
from ..schemas.clan import ClanOut
from ..schemas.hall import HallOut

router = APIRouter(
    prefix="/public",  # or you can add these to your main router
    tags=["public"]
)


@router.get("/county/{county_id}", response_model=CountyOut)
def get_clans_by_county(county_id: int, db: Session = Depends(get_db)):
    """
    Get all clans in a specific county.
    Used during reservation creation to show available clans for the user's county.
    """
    # Verify county exists
    county = db.query(County).filter(County.id == county_id).first()
    if not county:
        raise HTTPException(
            status_code=404,
            detail=f"المحافظة بالمعرف {county_id} غير موجودة"
        )

    # Format response to include allow_two_days from settings
    return county


# Get clans by county ID


@router.get("/clans/by-county/{county_id}", response_model=List[ClanOut])
def get_clans_by_county(county_id: int, db: Session = Depends(get_db)):
    """
    Get all clans in a specific county.
    Used during reservation creation to show available clans for the user's county.
    """
    # Verify county exists
    county = db.query(County).filter(County.id == county_id).first()
    if not county:
        raise HTTPException(
            status_code=404,
            detail=f"المحافظة بالمعرف {county_id} غير موجودة"
        )

    # Get clans with their settings to check allow_two_days
    clans = db.query(Clan).options(
        joinedload(Clan.settings),
        joinedload(Clan.county)
    ).filter(
        Clan.county_id == county_id
    ).order_by(Clan.id).all()

    if not clans:
        raise HTTPException(
            status_code=404,
            detail=f"لا توجد عشائر في محافظة {county.name}"
        )

    # Format response to include allow_two_days from settings
    result = []
    for clan in clans:
        clan_data = {
            "id": clan.id,
            "name": clan.name,
            "county_id": clan.county_id,
            "county_name": clan.county.name if clan.county else None,
            "description": getattr(clan, 'description', None),
            "allow_two_days": clan.settings.allow_two_day_reservations if clan.settings else False,
        }
        result.append(clan_data)

    return result


# Get halls by clan ID
@router.get("/halls/by-clan/{clan_id}", response_model=List[HallOut])
def get_halls_by_clan(clan_id: int, db: Session = Depends(get_db)):
    """
    Get all halls belonging to a specific clan.
    Used during reservation creation to show available halls for the selected clan.
    """
    # Verify clan exists
    clan = db.query(Clan).filter(Clan.id == clan_id).first()
    if not clan:
        raise HTTPException(
            status_code=404,
            detail=f"العشيرة بالمعرف {clan_id} غير موجودة"
        )

    # Get halls for this clan
    halls = db.query(Hall).filter(
        Hall.clan_id == clan_id
    ).all()

    if not halls:
        raise HTTPException(
            status_code=404,
            detail=f"لا توجد قاعات للعشيرة {clan.name}"
        )

    return halls
