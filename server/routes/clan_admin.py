"""
Clan Admin routes: CRUD grooms, halls, committees, clan settings.
"""
from datetime import datetime
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from httpx import delete
from sqlalchemy import or_
from sqlalchemy.orm import Session

from server.CRUD import clan_rules_crud
from server.models.reservation import Reservation, ReservationStatus
from server.models.reservation_clan_admin import ReservationSpecial, ReservationSpecialStatus
from server.schemas.clan import ClanOut
from server.schemas.clan_rules_schema import ClanRulesCreate, ClanRulesResponse, ClanRulesUpdate
from server.schemas.haia_committe import HaiaCreate, HaiaOut, HaiaUpdate
from server.schemas.madaih_committe import MadaihCreate, MadaihOut, MadaihUpdate
from server.routes.reservations import create_reservation
from server.schemas.reservation import ReservationCreate
from server.schemas.reservations_special import ReservationSpecialCreate, ReservationSpecialOut
from server.CRUD.clan_rules_crud import update
from ..auth_utils import get_current_user, get_db, require_role
from ..models.user import User, UserRole, UserStatus
from ..models.hall import Hall
from ..models.clan import Clan
from ..models.committee import HaiaCommittee, MadaehCommittee
from ..models.clan_settings import ClanSettings
from ..schemas.user import DeleteResponse, StatusUpdateRequest, UserCreate, UserOut
from ..schemas.hall import HallCreate, HallOut
# from ..schemas.madaih_committe import
from ..schemas.clan_settings import ClanSettingsCreate, ClanSettingsOut, ClanSettingsUpdate

router = APIRouter(
    prefix="/clan-admin",
    tags=["clan-admin"]
)

clan_admin_required = require_role([UserRole.clan_admin])


@router.get("/clan_info", response_model=ClanOut)
def get_clan_info(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    clan = db.query(Clan).filter(Clan.id == current.clan_id).first()
    if not clan:
        raise HTTPException(status_code=404, detail="العشيرة غير موجودة")
    return clan
# Grooms CRUD (view only those in own clan)

# Add this to your FastAPI router file (e.g., grooms.py or main.py)


@router.put("/grooms/{phone_number}/status")
async def update_groom_status(
    phone_number: str,
    status_request: StatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update groom account status (active/inactive)

    Args:
        phone_number: The groom's phone number (unique identifier)
        status_request: Contains the new status ("active" or "inactive")
        db: Database session

    Returns:
        Updated groom information
    """
    try:
        # Find the groom by phone number
        groom = db.query(User).filter(
            User.phone_number == phone_number,
            User.role == "groom"  # Ensure we're only updating grooms
        ).first()

        if not groom:
            raise HTTPException(
                status_code=404,
                detail=f"العريس برقم الهاتف {phone_number} غير موجود"
            )

        # Map string status to enum
        if status_request.status == "active":
            new_status = UserStatus.active
        else:  # "inactive"
            new_status = UserStatus.inactive

        # Update the status
        old_status = groom.status
        groom.status = new_status

        # Commit the changes
        db.commit()
        db.refresh(groom)

        logging.info(
            f"Updated groom {phone_number} status from {old_status} to {new_status}")

        return {
            "message": "تم تحديث حالة العريس بنجاح",
            "phone_number": phone_number,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "groom_name": f"{groom.first_name} {groom.last_name}",

        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error updating groom status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="خطأ داخلي في الخادم أثناء تحديث حالة العريس"
        )


# Optional: Get current status endpoint
@router.get("/grooms/{phone_number}/status")
async def get_groom_status(
    phone_number: str,
    db: Session = Depends(get_db)
):
    """
    Get current status of a groom

    Args:
        phone_number: The groom's phone number
        db: Database session

    Returns:
        Current groom status information
    """
    try:
        groom = db.query(User).filter(
            User.phone_number == phone_number,
            User.role == "groom"
        ).first()

        if not groom:
            raise HTTPException(
                status_code=404,
                detail=f"العريس برقم الهاتف {phone_number} غير موجود"
            )

        return {
            "phone_number": phone_number,
            "status": groom.status.value,
            "groom_name": f"{groom.first_name} {groom.last_name}",
            "created_at": groom.created_at,
            "is_active": groom.status == UserStatus.active
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting groom status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="خطأ داخلي في الخادم أثناء جلب حالة العريس"
        )
###


@router.get("/grooms", response_model=list[UserOut], dependencies=[Depends(clan_admin_required)])
def list_grooms(db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):
    return db.query(User).filter(
        User.role == UserRole.groom,
        User.clan_id == current.clan_id
    ).all()


# @router.delete("/grooms_deleted/{groom_phone}", response_model=UserOut, dependencies=[Depends(clan_admin_required)])
# def get_deleted_groom(groom_phone: str, db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):
#     groom = db.query(User).filter(
#         User.phone_number == groom_phone,
#         User.role == UserRole.groom,
#         User.clan_id == current.clan_id,
#     ).first()
#     if not groom:
#         raise HTTPException(
#             status_code=404, detail="العريس غير موجود أو ليس في عشيرتك")


#     db.delete(groom)
#     db.commit()
#     return {"message": f"تم حذف العريس برقم الهاتف {groom_phone} بنجاح."}


@router.delete("/grooms_deleted/{groom_phone}", response_model=DeleteResponse, dependencies=[Depends(clan_admin_required)])
def deleted_groom(groom_phone: str, db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):
    groom = db.query(User).filter(
        User.phone_number == groom_phone,
        User.role == UserRole.groom,
        User.clan_id == current.clan_id,
    ).first()
    if not groom:
        raise HTTPException(
            status_code=404, detail="العريس غير موجود أو ليس في عشيرتك")

    # Cancel all active reservations for this groom
    reservations_p = db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        Reservation.groom_id == groom.id,
        Reservation.status != ReservationStatus.pending_validation
    ).first()
    reservations_V = db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        Reservation.groom_id == groom.id,
        Reservation.status == ReservationStatus.validated
    ).first()

    if reservations_V:
        reservations_V.status = ReservationStatus.cancelled
        db.add(reservations_V)

    if reservations_p:
        reservations_p.status = ReservationStatus.cancelled
        db.add(reservations_p)

    db.commit()
    db.delete(groom)
    db.commit()
    return {"message": f"تم حذف العريس برقم الهاتف {groom_phone} بنجاح."}


########################## Halls CRUD  ##################################
# arived here


# post new hall
@router.post("/halls", response_model=HallOut, dependencies=[Depends(clan_admin_required)])
def create_hall(hall: HallCreate, db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):
    # Ensure hall is for clan admin's clan
    if hall.clan_id != current.clan_id:
        raise HTTPException(
            status_code=403, detail=f"أنت مسؤول عن العشيرة ذات المعرف {current.clan_id}، لكن المعرف الذي أدخلته {hall.clan_id} ليس معرف عشيرتك.")

    obj = Hall(name=hall.name, capacity=hall.capacity, clan_id=hall.clan_id)
    exest_hall_check = db.query(Hall).filter(
        Hall.clan_id == obj.clan_id,
        Hall.name == obj.name
    ).first()
    if exest_hall_check:
        raise HTTPException(status_code=400, detail="القاعة موجودة بالفعل")
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
# get all halls


@router.get("/halls", response_model=list[HallOut])
def list_halls(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(Hall).filter(Hall.clan_id == current.clan_id).all()


# update a hall by id

@router.put("/hall/{id}", response_model=HallOut, dependencies=[Depends(clan_admin_required)])
def update_hall(
    id: int,
    hall_update: HallCreate,
    db: Session = Depends(get_db),
    current: User = Depends(clan_admin_required)
):
    # Get the existing hall
    existing_hall = db.query(Hall).filter(
        Hall.id == id,
        Hall.clan_id == current.clan_id
    ).first()

    if not existing_hall:
        raise HTTPException(
            status_code=404,
            detail=f"القاعة ذات المعرف {id} غير موجودة أو ليس لديك صلاحية لتحديثها."
        )

    # Ensure the updated hall is still for the clan admin's clan
    if hall_update.clan_id != current.clan_id:
        raise HTTPException(
            status_code=403,
            detail=f"أنت مسؤول عن العشيرة ذات المعرف {current.clan_id}، لكن المعرف الذي أدخلته {hall_update.clan_id} ليس معرف عشيرتك."
        )

    # Update the hall fields
    existing_hall.name = hall_update.name
    existing_hall.capacity = hall_update.capacity
    existing_hall.clan_id = hall_update.clan_id

    try:
        db.commit()
        db.refresh(existing_hall)
        return existing_hall
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="حدث خطأ أثناء تحديث القاعة."
        )


# delet a hall by id
@router.delete("/hall/{id}", dependencies=[Depends(clan_admin_required)])
def delete_a_hall(id: int, db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):
    hall = db.query(Hall).filter(
        Hall.id == id,
        Hall.clan_id == current.clan_id
    ).first()
    if not hall:
        raise HTTPException(
            status_code=404, detail=f"القاعة ذات المعرف {id} غير موجودة.")

    db.delete(hall)
    db.commit()
    return {"message": f"تم حذف القاعة ذات المعرف {id} بنجاح."}


# ClanSettings CRUD (edit only own clan)


@router.get("/settings", response_model=ClanSettingsOut, dependencies=[Depends(get_current_user)])
def get_settings(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(ClanSettings).filter(ClanSettings.clan_id == current.clan_id).first()


@router.get("/setings/{clan_id}", response_model=ClanSettingsOut, dependencies=[Depends(get_current_user)])
def get_settings(clan_id: int, db: Session = Depends(get_db)):

    return db.query(ClanSettings).filter(ClanSettings.clan_id == clan_id).first()


@router.put("/settings/{clan__id}", response_model=ClanSettingsOut, dependencies=[Depends(clan_admin_required)])
def update_settings(clan__id: int, settings: ClanSettingsUpdate, db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):
    if clan__id != current.clan_id:
        raise HTTPException(status_code=403, detail="ليست عشيرتك")

    obj = db.query(ClanSettings).filter(
        ClanSettings.clan_id == current.clan_id).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="الإعدادات غير موجودة")

    settings_up = [
        "max_grooms_per_date",
        "years_max_reserv_GrooomFromOriginClan",
        "years_max_reserv_GroomFromOutClan",
        "allow_two_day_reservations",
        "validation_deadline_days",
        "allowed_months_single_day",
        "allowed_months_two_day",
        "calendar_years_ahead",
        "accept_invites_times",
        "days_to_accept_invites",
        "allow_cross_clan_reservations"

    ]

    if not any(getattr(settings, field) is not None for field in settings_up):
        raise HTTPException(status_code=400, detail="لا توجد حقول للتحديث")

    for field in settings_up:
        value = getattr(settings, field, None)
        if value is not None:
            setattr(obj, field, value)

    db.commit()
    db.refresh(obj)
    return obj


### clan rules ################


@router.post("/clan-rules", status_code=200, response_model=ClanRulesResponse, dependencies=[Depends(clan_admin_required)])
def create_clan_rules(
    rules_data: ClanRulesCreate,
    db: Session = Depends(get_db)
):
    """Create new clan rules (Admin only)"""
    # Check if rules already exist for this clan
    existing_rules = clan_rules_crud.get_by_clan_id(db, rules_data.clan_id)
    if existing_rules:
        raise HTTPException(
            status_code=400,
            detail="القواعد موجودة بالفعل لهذه العشيرة"
        )

    return clan_rules_crud.create(db, rules_data)


@router.get("/clan-rules/{rule_id}", response_model=ClanRulesResponse, dependencies=[Depends(clan_admin_required)])
def get_clan_rules_by_id(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Get clan rules by ID (Admin only)"""
    rules = clan_rules_crud.get_by_id(db, rule_id)
    if not rules:
        raise HTTPException(
            status_code=404,
            detail="قواعد العشيرة غير موجودة"
        )
    return rules


@router.get("/clan-rules/clan/{clan_id}", response_model=ClanRulesResponse, dependencies=[Depends(clan_admin_required)])
def get_clan_rules_by_clan_id(
    clan_id: int,
    db: Session = Depends(get_db)
):
    """Get clan rules by clan ID (Admin only)"""
    rules = clan_rules_crud.get_by_clan_id(db, clan_id)
    if not rules:
        raise HTTPException(
            status_code=404,
            detail="لم يتم العثور على قواعد لهذه العشيرة"
        )
    return rules


@router.put("/clan-rules/{rule_id}", response_model=ClanRulesResponse)
def update_clan_rules(
    rule_id: int,
    rules_data: ClanRulesUpdate,
    db: Session = Depends(get_db)
):
    """Update clan rules (Admin only)"""
    updated_rules = clan_rules_crud.update(db, rule_id, rules_data)
    if not updated_rules:
        raise HTTPException(
            status_code=404,
            detail="قواعد العشيرة غير موجودة"
        )
    return updated_rules


@router.delete("/clan-rules/{rule_id}", status_code=204)
def delete_clan_rules(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Delete clan rules (Admin only)"""
    success = clan_rules_crud.delete(db, rule_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="قواعد العشيرة غير موجودة"
        )

################ change payment status ###############


# a clan admin change the payment status


@router.post("/{reservation_id}/change_payment_status", response_model=dict, dependencies=[Depends(clan_admin_required)])
def cancel_a_groom_reservation(reservation_id: int, db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):

    resv = db.query(Reservation).filter(
        Reservation.id == reservation_id,
        Reservation.status != ReservationStatus.cancelled
    ).first()
    if not resv:
        raise HTTPException(
            status_code=404, detail=f"لا يوجد حجز معلق أو مصدق عليه   ")

    # Store previous status before toggling
    previous_status = resv.payment_valid

    # Toggle payment status
    resv.payment_valid = not resv.payment_valid

    db.commit()
    db.refresh(resv)

    # Create appropriate message based on new status
    status_message = "تم تأكيد دفع العريس بنجاح" if resv.payment_valid else "تم إلغاء تأكيد دفع العريس"

    return {
        "message": status_message,
        "reservation": {
            "id": resv.id,
            "groom_id": resv.groom_id,
            "payment_valid": resv.payment_valid,
            "previous_payment_status": previous_status,
            "status": resv.status.value
        }
    }

###########
# get all special reservations


@router.get("/special_reservations", response_model=List[ReservationSpecialOut])
def get_special_reservations(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    special_reservations = db.query(ReservationSpecial).filter(
        ReservationSpecial.county_id == current.county_id
    ).all()
    return special_reservations

#############


@router.put("/reservations/payment_update/{groom_id}", dependencies=[Depends(clan_admin_required)])
def update_payment(groom_id: int, db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):
    groom = db.query(User).filter(
        User.id == groom_id,
        User.role == UserRole.groom,
    ).first()
    if not groom:
        raise HTTPException(
            status_code=404, detail="العريس غير موجود أو ليس في عشيرتك")

    reservation_pending = db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        Reservation.clan_id == current.clan_id,
        Reservation.groom_id == groom.id,
        Reservation.status == ReservationStatus.pending_validation
    ).first()
    reservation_valid = db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        Reservation.clan_id == current.clan_id,
        Reservation.groom_id == groom.id,
        Reservation.status == ReservationStatus.validated
    ).first()

    if not reservation_pending and not reservation_valid:
        raise HTTPException(
            status_code=404, detail=f"لم يتم العثور على حجوزات معلقة أو مؤكدة لمعرف العريس {groom_id}")

    if reservation_pending:
        reservation_pending.status = ReservationStatus.validated
        reservation_pending.payment_valid = True  # Mark payment as valid
        db.add(reservation_pending)
        db.commit()
        return {"message": f"تم تحديث الحجز المعلق للعريس {groom_id} إلى مؤكد."}

    if reservation_valid:
        reservation_valid.status = ReservationStatus.validated
        reservation_valid.payment_valid = False  # Mark payment as valid
        db.add(reservation_valid)
        db.commit()
        return {"message": f"تم تحديث الحجز المؤكد للعريس {groom_id} إلى معلق."}

    return {"message": "لم يتم اتخاذ أي إجراء."}


################# clan manage a special reservation ################################

@router.post("/reserv_some_dates", dependencies=[Depends(clan_admin_required)])
def reserv_some_dates(
    reservation_create: ReservationSpecialCreate,
    db: Session = Depends(get_db),
    current: User = Depends(clan_admin_required)
):

    # Get admin's clan
    admin_clan = db.query(Clan).filter(Clan.id == current.clan_id).first()
    if not admin_clan:
        raise HTTPException(404, "العشيرة غير موجودة")

        # Check if there's already a special reservation for this date
    existing_special = db.query(ReservationSpecial).filter(
        ReservationSpecial.clan_id == current.clan_id,
        ReservationSpecial.county_id == current.county_id,
        ReservationSpecial.date == reservation_create.date,
        ReservationSpecial.status != ReservationSpecialStatus.cancelled
    ).first()

    if existing_special:
        raise HTTPException(400, "يوجد حجز خاص مسبق لهذا التاريخ")

    reservation = db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        or_(Reservation.date1 == reservation_create.date,
            Reservation.date2 == reservation_create.date,),
        Reservation.status != ReservationStatus.cancelled
    ).first()

    if reservation:
        raise HTTPException(
            status_code=400, detail=f"التاريخ محجوز بالفعل لعرس .")

    new_reservation = ReservationSpecial(
        clan_id=current.clan_id,
        county_id=current.county_id,
        reserv_name=reservation_create.reserv_name,
        reserv_desctiption=reservation_create.reserv_desctiption,
        date=reservation_create.date,
        full_name=reservation_create.full_name,
        home_address=reservation_create.home_address,
        phone_number=reservation_create.phone_number,
        status=ReservationSpecialStatus.validated,
        created_at=datetime.utcnow()
    )

    db.add(new_reservation)
    db.commit()
    db.refresh(new_reservation)

    return new_reservation


@router.get("/special_reservrations", response_model=List[ReservationSpecialOut], dependencies=[Depends(clan_admin_required)])
def get_all_special_reservations(
    db: Session = Depends(get_db),
    current: User = Depends(clan_admin_required)
):
    special_reserv = db.query(ReservationSpecial).filter(
        ReservationSpecial.clan_id == current.clan_id,
        ReservationSpecial.county_id == current.county_id
    ).all()

    return special_reserv


@router.put("/update_status_special_reserv/{reserv_id}", dependencies=[Depends(clan_admin_required)])
def update_status_special_reservation(
    reserv_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(clan_admin_required)
):
    reserv = db.query(ReservationSpecial).filter(
        ReservationSpecial.id == reserv_id,
        ReservationSpecial.county_id == current.county_id

    ).first()
    if not reserv:
        raise HTTPException(status_code=404, detail="الحجز الخاص غير موجود")

    reservation = db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        or_(Reservation.date1 == reserv.date,
            Reservation.date2 == reserv.date,),
        Reservation.status != ReservationStatus.cancelled
    ).first()

    if reservation:
        raise HTTPException(
            status_code=400, detail=f"التاريخ محجوز بالفعل لعرس .")

    if reserv.status == ReservationSpecialStatus.validated:
        reserv.status = ReservationSpecialStatus.cancelled
    else:
        reserv.status = ReservationSpecialStatus.validated

    db.add(reserv)
    db.commit()
    db.refresh(reserv)
    return {"message": "تم تفعيل الحجز الخاص بنجاح." if reserv.status == ReservationSpecialStatus.validated else "تم إلغاء الحجز الخاص بنجاح."}


# @router.delete("/special_reserv/{reserv_id}", dependencies=[Depends(clan_admin_required)])
# def delete_special_reservation(
#     reserv_id: int,
#     db: Session = Depends(get_db),
#     current: User = Depends(clan_admin_required)
# ):
#     reserv = db.query(ReservationSpecial).filter(
#         ReservationSpecial.id == reserv_id,
#         ReservationSpecial.clan_id == current.clan_id,
#         ReservationSpecial.county_id == current.county_id
#     ).first()

#     if not reserv:
#         raise HTTPException(status_code=404, detail="الحجز الخاص غير موجود")

#     db.delete(reserv)
#     db.commit()
#     return {"message": f"تم حذف الحجز الخاص ذو المعرف {reserv_id} بنجاح."}
