
# server\routes\grooms.py
"""
Groom self-service endpoints.
"""
import datetime
from typing import List
from server.CRUD import clan_rules_crud
from server.models import food
from server.models.clan import Clan
from server.models.committee import HaiaCommittee, MadaehCommittee
from server.models.county import County
from server.models.hall import Hall
from server.schemas.clan import ClanOut
from server.schemas.clan_rules_schema import ClanRulesResponse
from server.schemas.county import CountyOut
from server.schemas.food_type import FoodMenuOut
from server.schemas.haia_committe import HaiaOut
from server.schemas.hall import HallOut
from server.schemas.madaih_committe import MadaihOut
from server.utils.otp_utils import generate_otp_code, send_otp_to_user_by_twilo
from server.utils.phone_utils import validate_algerian_number, validate_algerian_number_for_guardian
from server.models.food import FoodMenu
from ..models.reservation import Reservation, ReservationStatus
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from ..auth_utils import get_current_user, get_db, require_role
from ..models.user import User, UserRole
from ..schemas.user import UserOut, UserUpdate

router = APIRouter(
    prefix="/groom",
    tags=["groom"]
)

groom_required = require_role([UserRole.groom])


@router.get("/profile", dependencies=[Depends(groom_required)])
def get_profile(db: Session = Depends(get_db), current: User = Depends(groom_required)):

    user = db.query(User).options(
        joinedload(User.county),
        joinedload(User.clan),
    ).filter(User.id == current.id).first()

    user_dic = {
        "id": user.id,
        "clan_id": user.clan_id,
        "county_id": user.county_id,
        "status": user.status,

        "created_at": user.created_at.isoformat() if user.created_at else None,

        # Joined data
        "clan_name": user.clan.name if user.clan else None,
        "county_name": user.county.name if user.county else None,


        # Personal information
        "first_name": user.first_name,
        "last_name": user.last_name,
        "father_name": user.father_name,
        "grandfather_name": user.grandfather_name,
        "birth_date": str(user.birth_date) if user.birth_date else None,
        "birth_address": user.birth_address,
        "home_address": user.home_address,
        "phone_number": user.phone_number,

        # Guardian information
        "guardian_name": user.guardian_name,
        "guardian_phone": user.guardian_phone,
        "guardian_home_address": user.guardian_home_address,
        "guardian_birth_address": user.guardian_birth_address,
        "guardian_birth_date": str(user.guardian_birth_date) if user.guardian_birth_date else None,
    }

    return user_dic


@router.put("/profile", response_model=UserOut, dependencies=[Depends(groom_required)])
def update_profile(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(groom_required)
):
    # Check if groom has any reservation (validated or pending)
    has_active_reservation = db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        Reservation.groom_id == current.id,
        Reservation.status != ReservationStatus.cancelled
    ).first()

    if not has_active_reservation:
        # ckeck county id exist
        county_exists = db.query(County).filter(
            County.id == user_update.county_id
        ).first()
        if not county_exists:
            raise HTTPException(
                status_code=404, detail=f"المحافظة بالمعرف {user_update.county_id} غير موجودة.")
        # check clan id exist
        clan_exists = db.query(Clan).filter(
            Clan.county_id == current.county_id,
            Clan.id == user_update.clan_id
        ).first()
        if not clan_exists:
            raise HTTPException(
                status_code=404, detail=f"العشيرة بالمعرف {user_update.clan_id} غير موجودة.")

    validate_algerian_number_for_guardian(user_update.guardian_phone)

    allowed_fields_if_reserved = {"guardian_name",
                                  "guardian_phone", "guardian_relation"}

    for field, value in user_update.dict(exclude_unset=True).items():
        if field == "phone_number":
            # on production i will dicomment it
            # Check if the phone number is different
            if value != current.phone_number:
                # Check if already taken
                existing = db.query(User).filter(
                    User.phone_number == value).first()
                if existing:
                    raise HTTPException(
                        status_code=400, detail="Phone number already in use.")

                # Generate OTP and send to new number
                temp_code = generate_otp_code()
                send_otp_to_user_by_twilo(value, temp_code)

                current.temp_phone_number = value
                current.temp_phone_otp_code = temp_code
                current.temp_phone_otp_expires_at = datetime.utcnow() + datetime.timedelta(hours=2)

                db.commit()
                return {
                    "message": "OTP sent to new phone number. Please verify to complete phone update."
                }
            continue  # skip setting phone directly

        if has_active_reservation:
            if field in allowed_fields_if_reserved:
                setattr(current, field, value)
        else:
            setattr(current, field, value)

    db.commit()
    db.refresh(current)
    return current


@router.delete("/profile", response_model=dict, dependencies=[Depends(groom_required)])
def delete_profile(
    db: Session = Depends(get_db),
    current: User = Depends(groom_required)
):
    groom = db.query(User).filter(User.id == current.id).first()
    if not groom:
        raise HTTPException(status_code=404, detail="العريس غير موجود")

    db.delete(groom)
    db.commit()
    return {"message": "تم حذف حسابك بنجاح."}


# get halls by groom
@router.get("/halls", response_model=list[HallOut])
def list_halls(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(Hall).filter(Hall.clan_id == current.clan_id).all()


# get all counties
@router.get("/counties", response_model=list[CountyOut])
def list_counties(db: Session = Depends(get_db)):
    return db.query(County).all()

# geting all clans


@router.get("/clans", response_model=list[ClanOut])
def list_clans(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    clans = db.query(Clan).filter(Clan.county_id == current.county_id).all()
    if not clans:
        raise HTTPException(status_code=404, detail="لا توجد عشائر")
    return clans


# get  all haiats by county_id
@router.get("/haia", response_model=list[HaiaOut])
def list_of_all_haia(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(HaiaCommittee).filter(HaiaCommittee.county_id == current.county_id).all()


# get  all Madaeh  by county_id
@router.get("/madaih_committe", response_model=list[MadaihOut])
def list_of_all_haia(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(MadaehCommittee).filter(MadaehCommittee.county_id == current.county_id).all()


# get  all Rulse of this clan
@router.get("/rules", response_model=list[MadaihOut])
def list_of_all_haia(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(MadaehCommittee).filter(MadaehCommittee.county_id == current.county_id).all()

######## clan rules ##################


@router.get("/clan-rules/{rule_id}", response_model=ClanRulesResponse)
def get_clan_rules(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Get clan rules by ID (Groom read-only access)"""
    rules = clan_rules_crud.get_by_id(db, rule_id)
    if not rules:
        raise HTTPException(
            status_code=404,
            detail="Clan rules not found"
        )
    return rules


@router.get("/clan-rules", response_model=ClanRulesResponse)
def get_clan_rules(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """Get clan rules by ID (Groom read-only access)"""
    rules = clan_rules_crud.get_by_clan_id(db, current.clan_id)
    if not rules:
        raise HTTPException(
            status_code=404,
            detail="Clan rules not found"
        )
    return rules


@router.get("/clan-rules/clan/{clan_id}", response_model=ClanRulesResponse)
def get_clan_rules_by_clan(
    clan_id: int,
    db: Session = Depends(get_db)
):
    """Get clan rules by clan ID (Groom read-only access)"""
    rules = clan_rules_crud.get_by_clan_id(db, clan_id)
    if not rules:
        raise HTTPException(
            status_code=404,
            detail="No rules found for this clan"
        )
    return rules
