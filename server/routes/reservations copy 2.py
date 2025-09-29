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


# # # get all Reservations


# @router.get("/all_reservations", response_model=list[ReservationOut])
# def list_clan_reservations(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
#     return db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,
#         Reservation.clan_id == current.clan_id).all()

# # get all pending Reservations


# @router.get("/pending_reservations", response_model=list[ReservationOut])
# def list_clan_reservations(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
#     return db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,

#         Reservation.clan_id == current.clan_id,
#         Reservation.status == ReservationStatus.pending_validation

#     ).all()

# # get all validated Reservations


# @router.get("/validated_reservations", response_model=list[ReservationOut])
# def list_clan_reservations(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
#     return db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,
#         Reservation.clan_id == current.clan_id,
#         Reservation.status == ReservationStatus.validated

#     ).all()


# # get all pending Reservations
# @router.get("/cancled_reservations", response_model=list[ReservationOut])
# def list_clan_reservations(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
#     return db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,
#         Reservation.clan_id == current.clan_id,
#         Reservation.status == ReservationStatus.cancelled

#     ).all()


# ############ post new reservation #################################


# @router.post("", response_model=ReservationCreateResponse, dependencies=[Depends(groom_required)])
# def create_reservation(resv_in: ReservationCreate, db: Session = Depends(get_db),
#                        current: User = Depends(groom_required)):
#     # Check for existing active reservation
#     if db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,
#         Reservation.groom_id == current.id,
#         Reservation.status != ReservationStatus.cancelled
#     ).first():
#         raise HTTPException(400, "You already have an active reservation")

#     # Determine target clan and validate
#     is_same_clan = resv_in.clan_id == current.clan_id
#     target_clan = None if is_same_clan else db.query(
#         Clan).filter(Clan.id == resv_in.clan_id).first()

#     if not is_same_clan:
#         if not target_clan:
#             raise HTTPException(400, "Target clan not found")
#         if target_clan.county_id != current.county_id:
#             raise HTTPException(
#                 400, "Cross-county reservations are not allowed")

#     # Get settings
#     settings = get_settings_for_clan(db, resv_in.clan_id)
#     if not settings:
#         raise HTTPException(
#             400, f"{'Clan' if is_same_clan else 'Target clan'} settings not found")

#     # Cross-clan specific checks
#     if not is_same_clan:
#         if not getattr(settings, 'allow_cross_clan_reservations', False):
#             raise HTTPException(
#                 400, "This clan does not accept reservations from other clans")

#     # Parse dates
#     date1 = resv_in.date1
#     date2 = date1 + timedelta(days=1) if resv_in.date2_bool else None

#     # Validate two-day reservation
#     if date2 and date1.month not in [int(m) for m in settings.allowed_months_two_day.split(',')]:
#         raise HTTPException(
#             400, f"Two-day reservations not allowed in this month{' for this clan' if not is_same_clan else ''}")

#     clan_name = f" in {target_clan.name} clan" if not is_same_clan else ""
#     dates_to_check = [date1] + ([date2] if date2 else [])

#     # Build base query filters
#     base_filters = [
#         Reservation.county_id == current.county_id,
#         Reservation.clan_id == resv_in.clan_id
#     ]

#     # Check solo wedding conflicts (validated)
#     solo_date_conditions = [
#         Reservation.date1 == date1,
#         Reservation.date2 == date1
#     ]
#     if date2:
#         solo_date_conditions.append(Reservation.date1 == date2)

#     solo_valid = db.query(Reservation).filter(
#         *base_filters,
#         Reservation.status == ReservationStatus.validated,
#         Reservation.allow_others == False,
#         or_(*solo_date_conditions)
#     ).first()

#     if solo_valid:
#         if solo_valid.date1 == date1 or (not date2 and solo_valid.date2 == date1):
#             raise HTTPException(
#                 400, f"This date {date1} is already reserved{clan_name}")
#         if date2:
#             if solo_valid.date2 == date1:
#                 raise HTTPException(
#                     400, f"This date {date1} is already reserved{clan_name}. Try the second day {date2}")
#             if solo_valid.date1 == date2:
#                 raise HTTPException(
#                     400, f"This date {date2} is already reserved{clan_name}. Try the first day {date1}")

#     # Check mass wedding conflicts (validated)
#     mass_date_conditions = [Reservation.date1 ==
#                             date1, Reservation.date2 == date1]
#     if date2:
#         mass_date_conditions.extend(
#             [Reservation.date1 == date2, Reservation.date2 == date2])

#     mass_valid = db.query(Reservation).filter(
#         *base_filters,
#         Reservation.status == ReservationStatus.validated,
#         Reservation.allow_others == True,
#         or_(*mass_date_conditions)
#     ).first()

#     if mass_valid:
#         if mass_valid.date2 and not date2 and mass_valid.date2 == date1:
#             raise HTTPException(
#                 400, f"Date {date1} reserved as second day of mass wedding{clan_name}")
#         if date2:
#             if mass_valid.date2 == date1:
#                 raise HTTPException(
#                     400, f"Date {date1} reserved as second day of mass wedding{clan_name}. Try {date2}")
#             if mass_valid.date1 == date2:
#                 raise HTTPException(
#                     400, f"Date {date2} reserved as mass wedding{clan_name}. Try first day {date1} only")
#         if mass_valid.date2 == date1:
#             raise HTTPException(
#                 400, f"Date {date1} reserved as second mass wedding{clan_name}. Join on {mass_valid.date1} if not full")

#     # Check pending mass weddings (if not already validated mass wedding)
#     if not mass_valid:
#         for d in dates_to_check:
#             if resv_in.join_to_mass_wedding and db.query(Reservation).filter(
#                 *base_filters,
#                 Reservation.status == ReservationStatus.pending_validation,
#                 Reservation.allow_others == True,
#                 or_(Reservation.date1 == d, Reservation.date2 == d)
#             ).first():
#                 raise HTTPException(
#                     400, f"Date {d} reserved but not validated{clan_name}. Try again in {settings.validation_deadline_days} days max")

#     # Check pending solo conflicts
#     pending_solo = db.query(Reservation).filter(
#         *base_filters,
#         Reservation.status == ReservationStatus.pending_validation,
#         Reservation.allow_others == False,
#         or_(*solo_date_conditions)
#     ).first()

#     if pending_solo:
#         if pending_solo.date1 == date1 or pending_solo.date2 == date1:
#             raise HTTPException(
#                 400, f"Date {date1} reserved but not validated{clan_name}. Check again in {settings.validation_deadline_days} days")
#         if date2 and pending_solo.date1 == date2:
#             raise HTTPException(
#                 400, f"Date {date2} reserved but not validated{clan_name}. Try booking only {date1}")

#     # Cross-clan priority check
#     if not is_same_clan and getattr(settings, 'prioritize_same_clan', True):
#         same_clan_dates = solo_date_conditions + \
#             ([Reservation.date2 == date2] if date2 else [])
#         if db.query(Reservation).filter(
#             *base_filters,
#             Reservation.groom_id.in_(db.query(User.id).filter(
#                 User.clan_id == resv_in.clan_id)),
#             Reservation.status == ReservationStatus.pending_validation,
#             or_(*same_clan_dates)
#         ).first():
#             raise HTTPException(
#                 400, f"Same-clan reservations have priority. Pending reservation from {target_clan.name} members exists")

#     # Capacity checks
#     for d in dates_to_check:
#         date_conditions = or_(Reservation.date1 == d, Reservation.date2 == d)

#         # Total capacity
#         total_count = db.query(Reservation).filter(
#             *base_filters,
#             Reservation.status != ReservationStatus.cancelled,
#             date_conditions
#         ).count()

#         if total_count >= settings.max_grooms_per_date:
#             raise HTTPException(400, f"Date {d} fully booked{clan_name}")

#         # Cross-clan capacity
#         if not is_same_clan:
#             cross_limit = getattr(
#                 settings, 'max_cross_clan_per_date', settings.max_grooms_per_date // 2)
#             cross_count = db.query(Reservation).filter(
#                 *base_filters,
#                 Reservation.status != ReservationStatus.cancelled,
#                 Reservation.groom_id.in_(db.query(User.id).filter(
#                     User.clan_id != resv_in.clan_id)),
#                 date_conditions
#             ).count()

#             if cross_count >= cross_limit:
#                 raise HTTPException(
#                     400, f"Cross-clan limit reached for {d}{clan_name}: {cross_count}/{cross_limit}")

#         # Mass wedding check
#         if 0 < total_count < settings.max_grooms_per_date and not resv_in.join_to_mass_wedding:
#             raise HTTPException(
#                 400, f"Date {d} reserved for mass wedding{clan_name}. Join if you'd like: {total_count}/{settings.max_grooms_per_date} grooms")

#     # Get hall
#     hall = db.query(Hall).filter(Hall.clan_id == resv_in.clan_id).first()
#     if not hall:
#         raise HTTPException(400, f"No hall found{clan_name}")

#     # Get groom and clan info for reservation
#     groom = db.query(User).filter(User.id == current.id).first()
#     clan = target_clan if not is_same_clan else db.query(
#         Clan).filter(Clan.id == current.clan_id).first()

#     # Create reservation
#     resv = Reservation(
#         groom_id=current.id,
#         clan_id=resv_in.clan_id,
#         date1=date1,
#         date2=date2,
#         date2_bool=bool(resv_in.date2_bool),
#         join_to_mass_wedding=bool(
#             resv_in.join_to_mass_wedding or resv_in.allow_others),
#         allow_others=bool(
#             resv_in.join_to_mass_wedding or resv_in.allow_others),
#         status=ReservationStatus.pending_validation,
#         created_at=datetime.utcnow(),
#         expires_at=datetime.utcnow() + timedelta(days=settings.validation_deadline_days),
#         hall_id=hall.id,
#         haia_committee_id=resv_in.haia_committee_id,
#         madaeh_committee_id=resv_in.madaeh_committee_id,
#         county_id=clan.county_id,

#         first_name=groom.first_name,
#         last_name=groom.last_name,
#         father_name=groom.father_name,
#         grandfather_name=groom.grandfather_name,

#         birth_date=groom.birth_date,
#         birth_address=groom.birth_address,
#         home_address=groom.home_address,
#         phone_number=groom.phone_number,

#         guardian_name=groom.guardian_name,
#         guardian_home_address=groom.guardian_home_address,
#         guardian_birth_address=groom.guardian_birth_address,
#         guardian_birth_date=groom.guardian_birth_date,
#         guardian_phone=groom.guardian_phone
#     )

#     db.add(resv)
#     db.commit()
#     db.refresh(resv)

# #     # 2. Generate PDF immediately after creation
#     # Generate PDF
#     pdf_path = generate_wedding_pdf(resv, output_dir="generated_pdfs", db=db)
#     resv.pdf_url = pdf_path
#     db.commit()
#     db.refresh(resv)

#     return {
#         "message": "Reservation created successfully",
#         "reservation_id": resv.id,
#         "pdf_url": f"/download/{resv.id}"
#     }


# @router.get("/download/{reservation_id}")
# def download_pdf(reservation_id: int):
#     pdf_file = f"generated_pdfs/reservation_{reservation_id}.pdf"
#     if not os.path.exists(pdf_file):
#         raise HTTPException(status_code=404, detail="PDF not found")
#     return FileResponse(pdf_file, media_type="application/pdf", filename=f"reservation_{reservation_id}.pdf")
# # -----------------------------------------------

# # a groom get his all reservations


# @router.get("/my_all_reservations", response_model=List[ReservationOut], dependencies=[Depends(groom_required)])
# def get_my_reservation(db: Session = Depends(get_db), current: User = Depends(groom_required)):
#     resv = db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,
#         Reservation.groom_id == current.id,
#     ).all()
#     if not resv:
#         raise HTTPException(status_code=404, detail="No reservations")
#     return resv


# # a groom get his pending reservation
# @router.get("/my_pending_reservation", response_model=ReservationOut, dependencies=[Depends(groom_required)])
# def get_my_reservation(db: Session = Depends(get_db), current: User = Depends(groom_required)):
#     resv = db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,
#         Reservation.groom_id == current.id,
#         Reservation.status == ReservationStatus.pending_validation
#     ).first()
#     if not resv:
#         raise HTTPException(status_code=404, detail="No pending reservation")
#     return resv


# # a groom get his validated reservation
# @router.get("/my_validated_reservation", response_model=ReservationOut, dependencies=[Depends(groom_required)])
# def get_my_reservation(db: Session = Depends(get_db), current: User = Depends(groom_required)):
#     resv = db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,
#         Reservation.groom_id == current.id,
#         Reservation.status == ReservationStatus.validated
#     ).first()
#     if not resv:
#         raise HTTPException(status_code=404, detail="No validated reservation")
#     return resv

# # a groom get his validated reservation


# @router.get("/my_cancelled_reservation", response_model=List[ReservationOut], dependencies=[Depends(groom_required)])
# def get_my_reservation(db: Session = Depends(get_db), current: User = Depends(groom_required)):
#     resv = db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,
#         Reservation.groom_id == current.id,
#         Reservation.status == ReservationStatus.cancelled
#     ).all()
#     if not resv:
#         raise HTTPException(status_code=404, detail="No cancled reservation")
#     return resv


# # a groom cancel his reservation if is on status of pending validation
# @router.post("/{groom_id}/cancel", response_model=ReservationOut, dependencies=[Depends(groom_required)])
# def cancel_my_reservation(groom_id: int, db: Session = Depends(get_db), current: User = Depends(groom_required)):
#     resv = db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,
#         Reservation.groom_id == groom_id,
#         Reservation.clan_id == current.clan_id,
#         Reservation.status != ReservationStatus.cancelled
#     ).first()
#     if groom_id != current.id:
#         raise HTTPException(
#             status_code=404, detail="should insurt your correct ID to cancel you reservation .")
#     if not resv:
#         raise HTTPException(
#             status_code=404, detail="Reservation not found")

#     if resv.status == ReservationStatus.validated:
#         raise HTTPException(
#             status_code=400, detail="Cannot cancel a validated reservation, contact you clan admin for more hellp.")

#     resv.status = ReservationStatus.cancelled
#     db.commit()
#     db.refresh(resv)
#     return resv


# # a clan admin valide a reservation by groom id
# @router.post("/{groom_id}/validate", response_model=ReservationOut, dependencies=[Depends(clan_admin_required)])
# def validate_reservation(groom_id: int, db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):
#     resv_duplicated_check = db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,
#         Reservation.groom_id == groom_id,
#         Reservation.clan_id == current.clan_id,
#         Reservation.status == ReservationStatus.validated
#     ).first()
#     if resv_duplicated_check:
#         raise HTTPException(
#             status_code=404, detail="the groom has an exist validated reservation .")

#     resv = db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,
#         Reservation.groom_id == groom_id,
#         Reservation.clan_id == current.clan_id,
#         Reservation.status == ReservationStatus.pending_validation

#     ).first()
#     if not resv:
#         raise HTTPException(
#             status_code=404, detail="Reservation not found")

#     resv.status = ReservationStatus.validated
#     db.commit()
#     db.refresh(resv)
#     return resv


# # a clan admin cancel a reservation by groom id
# @router.post("/{groom_id}/cancel_by_clan_admin", response_model=dict, dependencies=[Depends(clan_admin_required)])
# def cancel_a_groom_reservation(groom_id: int, db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):
#     # resv_validated = db.query(Reservation).filter(
#     #     Reservation.groom_id == groom_id,
#     #     Reservation.clan_id == current.clan_id,
#     #     Reservation.status == ReservationStatus.validated
#     # ).all()

#     # if len(resv_validated) == 0:
#     #     raise HTTPException(
#     #         status_code=404, detail="no reservation valide for this groom. ")

#     # print('resv_validated.count---------', len(resv_validated))
#     # if len(resv_validated) > 1:
#     #     raise HTTPException(
#     #         status_code=404, detail="Has more then one validated reservation !! ")

#     # check if the groom has a pending or validated reservation
#     resv = db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,
#         Reservation.groom_id == groom_id,
#         Reservation.clan_id == current.clan_id,
#         Reservation.status != ReservationStatus.cancelled
#     ).first()
#     if not resv:
#         raise HTTPException(
#             status_code=404, detail=f"no pending or validated reservation for this grom id {groom_id} .")

#     if resv.status == ReservationStatus.validated:
#         valid_cancel = True
#     elif resv.status == ReservationStatus.pending_validation:
#         valid_cancel = False

#     resv.status = ReservationStatus.cancelled
#     db.commit()
#     db.refresh(resv)

#     # return resv
#     return {
#         "message": "Reservation cancelled successfully" + (" (was on validated status)" if valid_cancel else "(was on pending_validation status)"),
#         "reservation": ReservationOut.from_orm(resv)
#     }


# # Add these updated endpoints to your FastAPI backend to return joined data
# # Option 2: Return empty dict with 200 status
# @router.delete("/delete_res/{reservation_id}", response_model=dict, dependencies=[Depends(get_current_user)])
# def delete_reservation(reservation_id: int, db: Session = Depends(get_db)):
#     resv = db.query(Reservation).filter(
#         Reservation.id == reservation_id,
#     ).first()
#     if not resv:
#         return {}  # Returns empty dict
#     db.delete(resv)
#     db.commit()
#     return {"message": "Reservation deleted successfully"}


# @router.get("/reservations/my_all_reservations")
# def get_my_all_reservations(
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Get all reservations for the current groom with joined data"""
#     reservations = db.query(Reservation).options(
#         joinedload(Reservation.clan),
#         joinedload(Reservation.county),
#         joinedload(Reservation.hall),
#         joinedload(Reservation.haia_committee),
#         joinedload(Reservation.madaeh_committee)
#     ).filter(Reservation.groom_id == current_user.id).all()

#     result = []
#     for reservation in reservations:
#         reservation_dict = {
#             "id": reservation.id,
#             "groom_id": reservation.groom_id,
#             "clan_id": reservation.clan_id,
#             "county_id": reservation.county_id,
#             "date1": str(reservation.date1) if reservation.date1 else None,
#             "date2": str(reservation.date2) if reservation.date2 else None,
#             "date2_bool": reservation.date2_bool,
#             "allow_others": reservation.allow_others,
#             "join_to_mass_wedding": reservation.join_to_mass_wedding,
#             "status": reservation.status,
#             "created_at": reservation.created_at.isoformat() if reservation.created_at else None,
#             "expires_at": reservation.expires_at.isoformat() if reservation.expires_at else None,

#             # Joined data
#             "clan_name": reservation.clan.name if reservation.clan else None,
#             "county_name": reservation.county.name if reservation.county else None,
#             "hall_name": reservation.hall.name if reservation.hall else None,
#             "hall_id": reservation.hall_id,

#             # Committee information
#             "haia_committee_id": reservation.haia_committee_id,
#             "haia_committee_name": reservation.haia_committee.name if reservation.haia_committee else None,
#             "madaeh_committee_id": reservation.madaeh_committee_id,
#             "madaeh_committee_name": reservation.madaeh_committee.name if reservation.madaeh_committee else None,

#             # Personal information
#             "pdf_url": reservation.pdf_url,
#             "first_name": reservation.first_name,
#             "last_name": reservation.last_name,
#             "father_name": reservation.father_name,
#             "grandfather_name": reservation.grandfather_name,
#             "birth_date": str(reservation.birth_date) if reservation.birth_date else None,
#             "birth_address": reservation.birth_address,
#             "home_address": reservation.home_address,
#             "phone_number": reservation.phone_number,

#             # Guardian information
#             "guardian_name": reservation.guardian_name,
#             "guardian_phone": reservation.guardian_phone,
#             "guardian_home_address": reservation.guardian_home_address,
#             "guardian_birth_address": reservation.guardian_birth_address,
#             "guardian_birth_date": str(reservation.guardian_birth_date) if reservation.guardian_birth_date else None,
#         }
#         result.append(reservation_dict)

#     return result


# @router.get("/reservations/my_pending_reservation")
# def get_my_pending_reservation(
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Get pending reservation for the current groom with joined data"""
#     reservation = db.query(Reservation).options(
#         joinedload(Reservation.clan),
#         joinedload(Reservation.county),
#         joinedload(Reservation.hall),
#         joinedload(Reservation.haia_committee),
#         joinedload(Reservation.madaeh_committee)
#     ).filter(
#         Reservation.groom_id == current_user.id,
#         Reservation.status == ReservationStatus.pending_validation
#     ).first()

#     if not reservation:
#         raise HTTPException(
#             status_code=404, detail="No pending reservation found")

#     return {
#         "id": reservation.id,
#         "groom_id": reservation.groom_id,
#         "clan_id": reservation.clan_id,
#         "county_id": reservation.county_id,
#         "date1": str(reservation.date1) if reservation.date1 else None,
#         "date2": str(reservation.date2) if reservation.date2 else None,
#         "date2_bool": reservation.date2_bool,
#         "allow_others": reservation.allow_others,
#         "join_to_mass_wedding": reservation.join_to_mass_wedding,
#         "status": reservation.status,
#         "created_at": reservation.created_at.isoformat() if reservation.created_at else None,
#         "expires_at": reservation.expires_at.isoformat() if reservation.expires_at else None,

#         # Joined data
#         "clan_name": reservation.clan.name if reservation.clan else None,
#         "county_name": reservation.county.name if reservation.county else None,
#         "hall_name": reservation.hall.name if reservation.hall else None,
#         "hall_id": reservation.hall_id,

#         # Committee information
#         "haia_committee_id": reservation.haia_committee_id,
#         "haia_committee_name": reservation.haia_committee.name if reservation.haia_committee else None,
#         "madaeh_committee_id": reservation.madaeh_committee_id,
#         "madaeh_committee_name": reservation.madaeh_committee.name if reservation.madaeh_committee else None,

#         # Personal information
#         "pdf_url": reservation.pdf_url,
#         "first_name": reservation.first_name,
#         "last_name": reservation.last_name,
#         "father_name": reservation.father_name,
#         "grandfather_name": reservation.grandfather_name,
#         "birth_date": str(reservation.birth_date) if reservation.birth_date else None,
#         "birth_address": reservation.birth_address,
#         "home_address": reservation.home_address,
#         "phone_number": reservation.phone_number,

#         # Guardian information
#         "guardian_name": reservation.guardian_name,
#         "guardian_phone": reservation.guardian_phone,
#         "guardian_home_address": reservation.guardian_home_address,
#         "guardian_birth_address": reservation.guardian_birth_address,
#         "guardian_birth_date": str(reservation.guardian_birth_date) if reservation.guardian_birth_date else None,
#     }


# @router.get("/reservations/my_validated_reservation")
# def get_my_validated_reservation(
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Get validated reservation for the current groom with joined data"""
#     reservation = db.query(Reservation).options(
#         joinedload(Reservation.clan),
#         joinedload(Reservation.county),
#         joinedload(Reservation.hall),
#         joinedload(Reservation.haia_committee),
#         joinedload(Reservation.madaeh_committee)
#     ).filter(
#         Reservation.groom_id == current_user.id,
#         Reservation.status == ReservationStatus.validated
#     ).first()

#     if not reservation:
#         raise HTTPException(
#             status_code=404, detail="No validated reservation found")

#     return {
#         "id": reservation.id,
#         "groom_id": reservation.groom_id,
#         "clan_id": reservation.clan_id,
#         "county_id": reservation.county_id,
#         "date1": str(reservation.date1) if reservation.date1 else None,
#         "date2": str(reservation.date2) if reservation.date2 else None,
#         "date2_bool": reservation.date2_bool,
#         "allow_others": reservation.allow_others,
#         "join_to_mass_wedding": reservation.join_to_mass_wedding,
#         "status": reservation.status,
#         "created_at": reservation.created_at.isoformat() if reservation.created_at else None,
#         "expires_at": reservation.expires_at.isoformat() if reservation.expires_at else None,

#         # Joined data
#         "clan_name": reservation.clan.name if reservation.clan else None,
#         "county_name": reservation.county.name if reservation.county else None,
#         "hall_name": reservation.hall.name if reservation.hall else None,
#         "hall_id": reservation.hall_id,

#         # Committee information
#         "haia_committee_id": reservation.haia_committee_id,
#         "haia_committee_name": reservation.haia_committee.name if reservation.haia_committee else None,
#         "madaeh_committee_id": reservation.madaeh_committee_id,
#         "madaeh_committee_name": reservation.madaeh_committee.name if reservation.madaeh_committee else None,

#         # Personal information
#         "pdf_url": reservation.pdf_url,
#         "first_name": reservation.first_name,
#         "last_name": reservation.last_name,
#         "father_name": reservation.father_name,
#         "grandfather_name": reservation.grandfather_name,
#         "birth_date": str(reservation.birth_date) if reservation.birth_date else None,
#         "birth_address": reservation.birth_address,
#         "home_address": reservation.home_address,
#         "phone_number": reservation.phone_number,

#         # Guardian information
#         "guardian_name": reservation.guardian_name,
#         "guardian_phone": reservation.guardian_phone,
#         "guardian_home_address": reservation.guardian_home_address,
#         "guardian_birth_address": reservation.guardian_birth_address,
#         "guardian_birth_date": str(reservation.guardian_birth_date) if reservation.guardian_birth_date else None,
#     }


# @router.get("/reservations/my_cancelled_reservation")
# def get_my_cancelled_reservations(
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Get all cancelled reservations for the current groom with joined data"""
#     reservations = db.query(Reservation).options(
#         joinedload(Reservation.clan),
#         joinedload(Reservation.county),
#         joinedload(Reservation.hall),
#         joinedload(Reservation.haia_committee),
#         joinedload(Reservation.madaeh_committee)
#     ).filter(
#         Reservation.groom_id == current_user.id,
#         Reservation.status == ReservationStatus.cancelled
#     ).all()

#     result = []
#     for reservation in reservations:
#         reservation_dict = {
#             "id": reservation.id,
#             "groom_id": reservation.groom_id,
#             "clan_id": reservation.clan_id,
#             "county_id": reservation.county_id,
#             "date1": str(reservation.date1) if reservation.date1 else None,
#             "date2": str(reservation.date2) if reservation.date2 else None,
#             "date2_bool": reservation.date2_bool,
#             "allow_others": reservation.allow_others,
#             "join_to_mass_wedding": reservation.join_to_mass_wedding,
#             "status": reservation.status,
#             "created_at": reservation.created_at.isoformat() if reservation.created_at else None,
#             "expires_at": reservation.expires_at.isoformat() if reservation.expires_at else None,

#             # Joined data
#             "clan_name": reservation.clan.name if reservation.clan else None,
#             "county_name": reservation.county.name if reservation.county else None,
#             "hall_name": reservation.hall.name if reservation.hall else None,
#             "hall_id": reservation.hall_id,

#             # Committee information
#             "haia_committee_id": reservation.haia_committee_id,
#             "haia_committee_name": reservation.haia_committee.name if reservation.haia_committee else None,
#             "madaeh_committee_id": reservation.madaeh_committee_id,
#             "madaeh_committee_name": reservation.madaeh_committee.name if reservation.madaeh_committee else None,

#             # Personal information
#             "pdf_url": reservation.pdf_url,
#             "first_name": reservation.first_name,
#             "last_name": reservation.last_name,
#             "father_name": reservation.father_name,
#             "grandfather_name": reservation.grandfather_name,
#             "birth_date": str(reservation.birth_date) if reservation.birth_date else None,
#             "birth_address": reservation.birth_address,
#             "home_address": reservation.home_address,
#             "phone_number": reservation.phone_number,

#             # Guardian information
#             "guardian_name": reservation.guardian_name,
#             "guardian_phone": reservation.guardian_phone,
#             "guardian_home_address": reservation.guardian_home_address,
#             "guardian_birth_address": reservation.guardian_birth_address,
#             "guardian_birth_date": str(reservation.guardian_birth_date) if reservation.guardian_birth_date else None,
#         }
#         result.append(reservation_dict)

#     return result

# # Update the cancel reservation endpoint to use reservation ID instead of groom ID


# @router.post("/reservations/{reservation_id}/cancel")
# def cancel_reservation(
#     reservation_id: int,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Cancel a reservation by its ID"""
#     reservation = db.query(Reservation).filter(
#         Reservation.id == reservation_id,
#         Reservation.groom_id == current_user.id
#     ).first()

#     if not reservation:
#         raise HTTPException(status_code=404, detail="Reservation not found")

#     if reservation.status == ReservationStatus.cancelled:
#         raise HTTPException(
#             status_code=400, detail="Reservation is already cancelled")

#     if reservation.status == ReservationStatus.validated:
#         raise HTTPException(
#             status_code=400, detail="Cannot cancel validated reservation")

#     reservation.status = ReservationStatus.cancelled
#     db.commit()

#     return {"message": "Reservation cancelled successfully"}

# # Also update the admin reservation endpoints with joined data


# @router.get("/reservations/all_reservations")
# def get_all_reservations(
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Get all reservations for the current clan admin's clan with joined data"""
#     reservations = db.query(Reservation).options(
#         joinedload(Reservation.clan),
#         joinedload(Reservation.county),
#         joinedload(Reservation.hall),
#         joinedload(Reservation.haia_committee),
#         joinedload(Reservation.madaeh_committee),
#         joinedload(Reservation.groom)
#     ).filter(Reservation.clan_id == current_user.clan_id).all()

#     result = []
#     for reservation in reservations:
#         reservation_dict = {
#             "id": reservation.id,
#             "groom_id": reservation.groom_id,
#             "clan_id": reservation.clan_id,
#             "county_id": reservation.county_id,
#             "date1": str(reservation.date1) if reservation.date1 else None,
#             "date2": str(reservation.date2) if reservation.date2 else None,
#             "date2_bool": reservation.date2_bool,
#             "allow_others": reservation.allow_others,
#             "join_to_mass_wedding": reservation.join_to_mass_wedding,
#             "status": reservation.status,
#             "created_at": reservation.created_at.isoformat() if reservation.created_at else None,
#             "expires_at": reservation.expires_at.isoformat() if reservation.expires_at else None,

#             # Joined data
#             "clan_name": reservation.clan.name if reservation.clan else None,
#             "county_name": reservation.county.name if reservation.county else None,
#             "hall_name": reservation.hall.name if reservation.hall else None,
#             "hall_id": reservation.hall_id,

#             # Committee information
#             "haia_committee_id": reservation.haia_committee_id,
#             "haia_committee_name": reservation.haia_committee.name if reservation.haia_committee else None,
#             "madaeh_committee_id": reservation.madaeh_committee_id,
#             "madaeh_committee_name": reservation.madaeh_committee.name if reservation.madaeh_committee else None,

#             # Groom information
#             "groom_first_name": reservation.groom.first_name if reservation.groom else None,
#             "groom_last_name": reservation.groom.last_name if reservation.groom else None,
#             "groom_phone_number": reservation.groom.phone_number if reservation.groom else None,

#             # Personal information from reservation
#             "pdf_url": reservation.pdf_url,
#             "first_name": reservation.first_name,
#             "last_name": reservation.last_name,
#             "father_name": reservation.father_name,
#             "grandfather_name": reservation.grandfather_name,
#             "birth_date": str(reservation.birth_date) if reservation.birth_date else None,
#             "birth_address": reservation.birth_address,
#             "home_address": reservation.home_address,
#             "phone_number": reservation.phone_number,

#             # Guardian information
#             "guardian_name": reservation.guardian_name,
#             "guardian_phone": reservation.guardian_phone,
#             "guardian_home_address": reservation.guardian_home_address,
#             "guardian_birth_address": reservation.guardian_birth_address,
#             "guardian_birth_date": str(reservation.guardian_birth_date) if reservation.guardian_birth_date else None,
#         }
#         result.append(reservation_dict)

#     return result


# # Add these routes to your reservation.py file
# # Pydantic models for the calendar endpoints
# # Calendar endpoints for validated and pending reservations

# @router.get("/validated-dates/{clan_id}")
# def get_validated_dates(
#     clan_id: int,
#     db: Session = Depends(get_db),
# ):
#     """
#     Get all dates with validated reservations for a specific clan
#     """
#     try:
#         # Validate clan exists
#         clan = db.query(Clan).filter(Clan.id == clan_id).first()
#         if not clan:
#             raise HTTPException(status_code=404, detail="Clan not found")

#         # Get clan settings
#         settings = get_settings_for_clan(db, clan_id)
#         if not settings:
#             raise HTTPException(
#                 status_code=404, detail="Clan settings not found")

#         # Get all validated reservations for the clan
#         reservations = db.query(Reservation).filter(
#             Reservation.clan_id == clan_id,
#             Reservation.status == ReservationStatus.validated
#         ).all()

#         # Return the dates column only
#         for res in reservations:
#             res.date1 = str(res.date1) if res.date1 else None
#             res.date2 = str(res.date2) if res.date2 else None

#         return reservations

#     except Exception as e:
#         print(f"Error in get_validated_dates: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Error fetching validated dates: {str(e)}")


# @router.get("/pending-dates/{clan_id}")
# def get_pending_dates(
#     clan_id: int,
#     db: Session = Depends(get_db),
# ):
#     """
#     Get all dates with pending_validation reservations for a specific clan
#     """
#     try:
#         # Validate clan exists
#         clan = db.query(Clan).filter(Clan.id == clan_id).first()
#         if not clan:
#             raise HTTPException(status_code=404, detail="Clan not found")

#         # Get clan settings
#         settings = get_settings_for_clan(db, clan_id)
#         if not settings:
#             raise HTTPException(
#                 status_code=404, detail="Clan settings not found")

#         # Get all pending_validation reservations for the clan
#         reservations = db.query(Reservation).filter(
#             Reservation.clan_id == clan_id,
#             Reservation.status == ReservationStatus.pending_validation
#         ).all()

#         # Return the dates column only
#         for res in reservations:
#             res.date1 = str(res.date1) if res.date1 else None
#             res.date2 = str(res.date2) if res.date2 else None

#         return reservations

#     except Exception as e:
#         print(f"Error in get_pending_dates: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Error fetching pending dates: {str(e)}")
