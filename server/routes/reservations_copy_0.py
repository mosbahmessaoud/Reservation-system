# """
# Reservation routes for grooms and clan admins.
# """
# from typing import List, Dict, Optional
# from calendar import monthrange
# from typing import List, Optional
# from sqlalchemy.orm import joinedload
# import os
# from typing import List
# from fastapi import APIRouter, Depends, HTTPException
# from fastapi.responses import FileResponse
# from grpc import Status
# from pydantic import BaseModel
# from regex import D
# from sqlalchemy.orm import Session
# from sqlalchemy import and_, exists, or_
# from datetime import date, timedelta, datetime

# from server.models.clan import Clan
# from server.models.hall import Hall
# from server.utils.pdf_generator import generate_wedding_pdf
# from ..auth_utils import get_current_user, get_db, require_role
# from ..models.user import User, UserRole
# from ..models.reservation import Reservation, ReservationStatus
# from ..models.clan_settings import ClanSettings
# from ..schemas.reservation import ReservationCreate, ReservationCreateResponse, ReservationOut


# router = APIRouter(
#     prefix="/reservations",
#     tags=["reservations"]
# )
# groom_required = require_role([UserRole.groom])
# clan_admin_required = require_role([UserRole.clan_admin])


# def get_settings_for_clan(db, clan_id):
#     return db.query(ClanSettings).filter(ClanSettings.clan_id == clan_id).first()


# @router.post("/", response_model=ReservationOut, dependencies=[Depends(groom_required)])
# def create_reservation(resv_in: ReservationCreate, db: Session = Depends(get_db), current: User = Depends(groom_required)):
#     # Only allow one active reservation per groom

#     # Check if the groom already has an active reservation
#     active = db.query(Reservation).filter(
#         Reservation.groom_id == current.id,
#         Reservation.status != ReservationStatus.cancelled
#     ).first()
#     if active:
#         raise HTTPException(
#             status_code=400, detail="You already have an active reservation")

# # Check if the groom is part of a clan
#     print('====================  ', db, current.clan_id)
#     settings = get_settings_for_clan(db, current.clan_id)
#     if not settings:
#         raise HTTPException(status_code=400, detail="Clan settings not found")

#     date1 = resv_in.date1

#     date2 = date1 + timedelta(days=1) if resv_in.date2_bool == True else None

#     month = date1.month
#     allowed_months_two = [int(m)
#                           for m in settings.allowed_months_two_day.split(',')]

# # Check if the month is allowed for two-day reservations
#     if date2:
#         if month not in allowed_months_two:
#             raise HTTPException(
#                 status_code=400, detail="Two-day reservations not allowed in this month, make one day reservation please")

# ################## checks for the solo wedding #################
#     reserved_valid = db.query(Reservation).filter(
#         and_(
#             Reservation.clan_id == current.clan_id,
#             or_(
#                 Reservation.date1 == date1,
#                 Reservation.date1 == date2 if date2 else None,
#                 Reservation.date2 == date1 if Reservation.date2 else None),
#             Reservation.status == ReservationStatus.validated,
#             Reservation.allow_others == False
#         )
#     ).first()
#     if reserved_valid:
#         print('reserved_valid.date1 ============= ', reserved_valid.date1)

#     if reserved_valid and reserved_valid.date1 == date1:
#         raise HTTPException(
#             status_code=400,
#             detail=f"this date {date1} is reserved  ."
#         )

#     print('daate 11 ========== ', date1)
#     print('daate 22 =========== ', date2)
#     print('resv_in daate 11 ============ ', resv_in.date1)
#     print('resv_in daate 22 ========== ', resv_in.date2)
#     if reserved_valid:
#         print('reserved_valid.date1 ============= ', reserved_valid.date1)
#     if reserved_valid and reserved_valid.date2 and reserved_valid.date2 == date1:
#         raise HTTPException(
#             status_code=400,
#             detail=f"This date {date1} is already reserved. You can only reserve the second day {date2} might still be available."

#         )

#     if reserved_valid and date2 and reserved_valid.date1 == date2:
#         raise HTTPException(
#             status_code=400,
#             detail=f"This date {date2} is already reserved. You can only reserve the first day {date1} might still be available."
#         )


# # -------- end chek of solo wedding-----------


# ################## checks for the mass wedding #################
# # .............. check for the vaidated reservation...................
#     mass_conditions = [Reservation.date1 == date1, Reservation.date2 == date1]

#     if date2:
#         mass_conditions.extend([
#             Reservation.date1 == date2,
#             Reservation.date2 == date2
#         ])

#     reserved_valid_mass = db.query(Reservation).filter(
#         and_(
#             Reservation.clan_id == current.clan_id,
#             or_(*mass_conditions),
#             Reservation.status == ReservationStatus.validated,
#             Reservation.allow_others == True
#         )
#     ).first()

#     if date2:
#         print('date2 -------------------------------', date2)
#     if reserved_valid_mass:
#         print('reserved_valid_mass.date1 --------------------------------------',
#               reserved_valid_mass.date1)
#     if reserved_valid_mass and reserved_valid_mass.date2 and not date2 and reserved_valid_mass.date2 == date1:
#         raise HTTPException(
#             status_code=400,
#             detail=f"This date {date1} is already reserved as a second day of a mass wedding ."
#         )
#     if reserved_valid_mass and reserved_valid_mass.date2 and reserved_valid_mass.date2 == date1:
#         raise HTTPException(
#             status_code=400,
#             detail=f"This date {date1} is already reserved as a second day of a mass wedding . You can reserve the second day only {date2} , might still be available."
#         )

#     if reserved_valid_mass and date2 and reserved_valid_mass.date1 == date2:
#         raise HTTPException(
#             status_code=400,
#             detail=f"This date {date2} is already reserved as a mass wedding . You can reserve the first day {date1} only , might still be available."

#         )

#     if date1:
#         print('date1------------------', date1)
#     if reserved_valid_mass:
#         print('reserved_valid_mass.date2------------------',
#               reserved_valid_mass.date2)
#     if reserved_valid_mass and reserved_valid_mass.date2 and reserved_valid_mass.date2 == date1:
#         raise HTTPException(
#             status_code=400,
#             detail=f"This date {date1} is already reserved as a seconde mass wedding . You can reserve with the mass widdign on this day {reserved_valid_mass.date1}if is not full booking  ."

#         )
#     if reserved_valid_mass:
#         skip = True
#     else:
#         skip = False

# # .............. check for the pending_validation reservation...................

#     if skip == False:
#         for d in [date1] + ([date2] if date2 else []):
#             pending_validation_reserv = db.query(Reservation).filter(
#                 Reservation.clan_id == current.clan_id,
#                 (Reservation.date1 == d) | (Reservation.date2 == d),
#                 Reservation.status == ReservationStatus.pending_validation,
#                 Reservation.allow_others == True
#             ).all()

#             if len(pending_validation_reserv) > 0 and resv_in.join_to_mass_wedding == True:
#                 raise HTTPException(
#                     status_code=400,
#                     detail=f"Date {d} is already reserved , but his statue is not validated yet , so if you wanna reserv a mass wedding with him come back next days (max at {settings.validation_deadline_days} days ) to chek if hi valide his date you can joine with him , or go to choos another day."
#                 )
# # -------- end chek of mass wedding-----------

# ################## checks for both (solo and mass wedding) #####################

# # .............. check for the pending_validation reservation...................

#     existing_resv = db.query(Reservation).filter(
#         Reservation.clan_id == current.clan_id,
#         or_(
#             Reservation.date1 == date1,
#             Reservation.date1 == date2 if resv_in.date2 else None,
#             Reservation.date2 == date1 if Reservation.date2 else None),
#         Reservation.status == ReservationStatus.pending_validation,
#         Reservation.allow_others == False
#     ).first()
#     if existing_resv and (existing_resv.date1 == date1 or existing_resv.date2 == date1):
#         raise HTTPException(
#             status_code=400,
#             detail=f"this date{date1} is reserved but not validated yet , so you can come back on next days max a 10 days to check if the date is empty or not  ."
#         )
#     if existing_resv and existing_resv.date1 == date2 if resv_in.date2 else None:
#         raise HTTPException(
#             status_code=400,
#             detail=f"this date{date2} is reserved but not validated yet , so you can come back on next days max a 10 days to check if the date is empty or not  , or you can reserve just one day on the first day {date1} brobably is empty ."
#         )


# # .............. check for both validated and pending_validation reservation...................

# # check if Fully booked  or not

#     for d in [date1] + ([date2] if date2 else []):
#         n = db.query(Reservation).filter(
#             Reservation.clan_id == current.clan_id,
#             (Reservation.date1 == d) | (Reservation.date2 == d),
#             Reservation.status != ReservationStatus.cancelled,
#         ).count()

#         if n >= settings.max_grooms_per_date:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Date {d} is fully booked. Please choose another day."
#             )

#         # If there are already other grooms on this date (but it's not full yet)
#         if n > 0 and resv_in.join_to_mass_wedding == False and n < settings.max_grooms_per_date:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"this date {d} already reserved by a mass wedding but is not full booked yet you can join with them , so is including {n} groom by max as {settings.max_grooms_per_date}. "
#             )
#         if n == 0 and resv_in.join_to_mass_wedding == True:
#             continue
#         if n == 0:
#             continue


# ############################ making the reservation ############################

#         # Create reservation
#     expires_at = datetime.utcnow() + timedelta(days=settings.validation_deadline_days)
#     resv = Reservation(
#         groom_id=current.id,
#         clan_id=current.clan_id,
#         date1=date1,
#         date2=date2,
#         date2_bool=resv_in.date2_bool or False,
#         # join_to_mass_wedding=resv_in.join_to_mass_wedding or False,
#         join_to_mass_wedding=bool(
#             resv_in.join_to_mass_wedding) or bool(resv_in.allow_others),

#         # allow_others=resv_in.join_to_mass_wedding if resv_in.join_to_mass_wedding == True or resv_in.allow_others else False,
#         allow_others=bool(resv_in.join_to_mass_wedding) or bool(
#             resv_in.allow_others),

#         status=ReservationStatus.pending_validation,
#         created_at=datetime.utcnow(),
#         expires_at=expires_at,
#         hall_id=None,
#         ceremony_committee_id=None,
#         madaeh_committee_id=None
#     )
#     db.add(resv)
#     db.commit()
#     db.refresh(resv)
#     return resv


# @router.get("/my", response_model=ReservationOut, dependencies=[Depends(groom_required)])
# def get_my_reservation(db: Session = Depends(get_db), current: User = Depends(groom_required)):
#     resv = db.query(Reservation).filter(
#         Reservation.groom_id == current.id,
#         Reservation.status != ReservationStatus.cancelled
#     ).first()
#     if not resv:
#         raise HTTPException(status_code=404, detail="No active reservation")
#     return resv


# @router.post("/{resv_id}/cancel", response_model=ReservationOut, dependencies=[Depends(groom_required)])
# def cancel_my_reservation(resv_id: int, db: Session = Depends(get_db), current: User = Depends(groom_required)):
#     resv = db.query(Reservation).filter(
#         Reservation.id == resv_id,
#         Reservation.groom_id == current.id
#     ).first()
#     if not resv or resv.status == ReservationStatus.cancelled:
#         raise HTTPException(status_code=404, detail="Reservation not found")
#     if resv.status == ReservationStatus.validated:
#         raise HTTPException(
#             status_code=400, detail="Cannot cancel a validated reservation")
#     resv.status = ReservationStatus.cancelled
#     db.commit()
#     db.refresh(resv)
#     return resv

# # Clan admin: approve or reject (validate) a reservation


# @router.post("/{resv_id}/validate", response_model=ReservationOut, dependencies=[Depends(clan_admin_required)])
# def validate_reservation(resv_id: int, db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):
#     resv = db.query(Reservation).filter(
#         Reservation.id == resv_id,
#         Reservation.clan_id == current.clan_id
#     ).first()
#     if not resv:
#         raise HTTPException(status_code=404, detail="Reservation not found")
#     resv.status = ReservationStatus.validated
#     db.commit()
#     db.refresh(resv)
#     return resv


# @router.get("/clan", response_model=list[ReservationOut], dependencies=[Depends(clan_admin_required)])
# def list_clan_reservations(db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):
#     return db.query(Reservation).filter(Reservation.clan_id == current.clan_id).all()
