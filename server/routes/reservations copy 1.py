# """
# Reservation routes for grooms and clan admins.
# """
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
# from ..schemas.reservation import ReservationCreate, ReservationOut

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


# class ReservationCreateResponse(BaseModel):
#     message: str
#     reservation_id: int
#     pdf_url: str


# @router.post("/", response_model=ReservationCreateResponse, dependencies=[Depends(groom_required)])
# def create_reservation(resv_in: ReservationCreate, db: Session = Depends(get_db), current: User = Depends(groom_required)):
#     # Only allow one active reservation per groom
#  # ─────── Basic Checks ─────────────────────────────────────────────
#     # Check if user already has active reservation
#     active = db.query(Reservation).filter(
#         Reservation.county_id == current.county_id,
#         Reservation.groom_id == current.id,
#         Reservation.status != ReservationStatus.cancelled
#     ).first()
#     if active:
#         raise HTTPException(
#             status_code=400, detail="You already have an active reservation")

# ##### on case user reserv on his clan ###########
#     if resv_in.clan_id == current.clan_id:
#                 # Check for clan settings
#                 settings = get_settings_for_clan(db, current.clan_id)
#                 if not settings:
#                     raise HTTPException(status_code=400, detail="Clan settings not found")

#                 # Parse and derive dates
#                 date1 = resv_in.date1
#                 date2 = date1 + timedelta(days=1) if resv_in.date2_bool else None
#                 month = date1.month

#                 if date2 and month not in [int(m) for m in settings.allowed_months_two_day.split(',')]:
#                     raise HTTPException(
#                         status_code=400, detail="Two-day reservations not allowed in this month. Please reserve only one day.")

#                 # ─────── Solo Wedding Validation ─────────────────────────────────
#                 reserved_valid = db.query(Reservation).filter(
#                     Reservation.county_id == current.county_id,
#                     Reservation.clan_id == current.clan_id,
#                     Reservation.status == ReservationStatus.validated,
#                     Reservation.allow_others == False,
#                     or_(
#                         Reservation.date1 == date1,
#                         Reservation.date1 == date2 if date2 else False,
#                         Reservation.date2 == date1 if date1 else False
#                     )
#                 ).first()

#                 if reserved_valid:
#                     if reserved_valid.date1 == date1:
#                         raise HTTPException(
#                             status_code=400, detail=f"This date {date1} is already reserved.")
#                     if date2 != None:
#                         if reserved_valid.date2 == date1:
#                             raise HTTPException(
#                                 status_code=400, detail=f"This date {date1} is already reserved. You can try the second day {date2}.")
#                         if reserved_valid.date1 == date2:
#                             raise HTTPException(
#                                 status_code=400, detail=f"This date {date2} is already reserved. You can try the first day {date1}.")
#                     elif date2 == None:
#                         if reserved_valid.date2 == date1:
#                             raise HTTPException(
#                                 status_code=400, detail=f"This date {date1} is already reserved.")

#                 # ─────── Validated Mass Wedding Conflict ─────────────────────────
#                 mass_conditions = [Reservation.date1 == date1, Reservation.date2 == date1]
#                 if date2:
#                     mass_conditions.extend(
#                         [Reservation.date1 == date2, Reservation.date2 == date2])

#                 reserved_valid_mass = db.query(Reservation).filter(
#                     Reservation.county_id == current.county_id,
#                     Reservation.clan_id == current.clan_id,
#                     Reservation.status == ReservationStatus.validated,
#                     Reservation.allow_others == True,
#                     or_(*mass_conditions)
#                 ).first()

#                 if reserved_valid_mass:
#                     if reserved_valid_mass.date2 and not date2 and reserved_valid_mass.date2 == date1:
#                         raise HTTPException(
#                             status_code=400, detail=f"This date {date1} is already reserved as a second day of a mass wedding.")
#                     if reserved_valid_mass.date2 == date1:
#                         raise HTTPException(
#                             status_code=400, detail=f"This date {date1} is already reserved as a second day of a mass wedding. You may reserve the second day {date2} if it's still available.")
#                     if date2 and reserved_valid_mass.date1 == date2:
#                         raise HTTPException(
#                             status_code=400, detail=f"This date {date2} is already reserved as a mass wedding. You can reserve only the first day {date1}, if its still avaliable .")
#                     if reserved_valid_mass.date2 == date1:
#                         raise HTTPException(
#                             status_code=400, detail=f"This date {date1} is already reserved as a second mass wedding. You may join the wedding on {reserved_valid_mass.date1} if not full.")

#                 skip = bool(reserved_valid_mass)

#                 # ─────── Pending Mass Wedding Join Requests ──────────────────────
#                 if not skip:
#                     for d in [date1] + ([date2] if date2 else []):
#                         pending_mass = db.query(Reservation).filter(
#                             Reservation.county_id == current.county_id,
#                             Reservation.clan_id == current.clan_id,
#                             Reservation.status == ReservationStatus.pending_validation,
#                             Reservation.allow_others == True,
#                             or_(Reservation.date1 == d, Reservation.date2 == d)
#                         ).all()

#                         if pending_mass and resv_in.join_to_mass_wedding:
#                             raise HTTPException(
#                                 status_code=400,
#                                 detail=f"Date {d} is reserved but not yet validated. Try again in next {settings.validation_deadline_days} days as max, or choose another date."
#                             )

#                 # ─────── Pending Solo Wedding Conflicts ──────────────────────────
#                 existing_resv = db.query(Reservation).filter(
#                     Reservation.county_id == current.county_id,
#                     Reservation.clan_id == current.clan_id,
#                     Reservation.status == ReservationStatus.pending_validation,
#                     Reservation.allow_others == False,
#                     or_(
#                         Reservation.date1 == date1,
#                         Reservation.date1 == date2 if date2 else False,
#                         Reservation.date2 == date1 if date1 else False
#                     )
#                 ).first()

#                 if existing_resv:
#                     if existing_resv.date1 == date1 or existing_resv.date2 == date1:
#                         raise HTTPException(
#                             status_code=400, detail=f"This date {date1} is reserved but not yet validated. Please check again in {settings.validation_deadline_days} days.")
#                     if date2 and existing_resv.date1 == date2:
#                         raise HTTPException(
#                             status_code=400, detail=f"This date {date2} is reserved but not validated yet. Try booking only {date1}.")

#                 # ─────── Capacity Checks (Both Solo & Mass) ──────────────────────
#                 for d in [date1] + ([date2] if date2 else []):
#                     n = db.query(Reservation).filter(
#                         Reservation.county_id == current.county_id,
#                         Reservation.clan_id == current.clan_id,
#                         Reservation.status != ReservationStatus.cancelled,
#                         or_(Reservation.date1 == d, Reservation.date2 == d)
#                     ).count()

#                     if n >= settings.max_grooms_per_date:
#                         raise HTTPException(
#                             status_code=400, detail=f"Date {d} is fully booked.")

#                     if n > 0 and not resv_in.join_to_mass_wedding and n < settings.max_grooms_per_date:
#                         raise HTTPException(
#                             status_code=400,
#                             detail=f"Date {d} is reserved for mass wedding. You can join if you'd like. Currently: {n}/{settings.max_grooms_per_date} grooms."
#                         )

#                     hall = db.query(Hall).filter(
#                         Hall.clan_id == current.clan_id,
#                     ).first()

#                     ## making the reservation ##

#                     # Create reservation
#                 # expires_at = datetime.utcnow() + timedelta(days=settings.validation_deadline_days)
#                 # resv = Reservation(
#                 #     groom_id=current.id,
#                 #     clan_id=current.clan_id,
#                 #     date1=date1,
#                 #     date2=date2,
#                 #     date2_bool=resv_in.date2_bool or False,
#                 #     join_to_mass_wedding=bool(
#                 #         resv_in.join_to_mass_wedding) or bool(resv_in.allow_others),
#                 #     allow_others=bool(resv_in.join_to_mass_wedding) or bool(
#                 #         resv_in.allow_others),

#                 #     status=ReservationStatus.pending_validation,
#                 #     created_at=datetime.utcnow(),
#                 #     expires_at=expires_at,
#                 #     hall_id=hall.id,
#                 #     haia_committee_id=None,
#                 #     madaeh_committee_id=None
#                 # )
#                 # Create reservation
#     ############ on cas user reserv on other clan ###########
#     elif resv_in.clan_id != current.clan_id:

#             # Get target clan information
#             target_clan = db.query(Clan).filter(Clan.id == resv_in.clan_id).first()
#             if not target_clan:
#                 raise HTTPException(status_code=400, detail="Target clan not found")
            
#             # Check if target clan is in the same county
#             if target_clan.county_id != current.county_id:
#                 raise HTTPException(
#                     status_code=400, 
#                     detail="Cross-county reservations are not allowed. You can only reserve within your county."
#                 )
            
#             # Get target clan settings
#             settings = get_settings_for_clan(db, resv_in.clan_id)
#             if not settings:
#                 raise HTTPException(status_code=400, detail="Target clan settings not found")
            
#             # Check if cross-clan reservations are allowed
#             if not getattr(settings, 'allow_cross_clan_reservations', False):
#                 raise HTTPException(
#                     status_code=400, 
#                     detail="This clan does not accept reservations from other clans"
#                 )
            
#             # Parse and derive dates
#             date1 = resv_in.date1
#             date2 = date1 + timedelta(days=1) if resv_in.date2_bool else None
#             month = date1.month
            
#             # Check two-day reservation policy for cross-clan
#             if date2 and month not in [int(m) for m in settings.allowed_months_two_day.split(',')]:
#                 raise HTTPException(
#                     status_code=400, 
#                     detail="Two-day reservations not allowed in this month for this clan. Please reserve only one day."
#                 )
            
#             # ─────── Solo Wedding Validation (Cross-Clan) ─────────────────────
#             reserved_valid = db.query(Reservation).filter(
#                 Reservation.county_id == current.county_id,
#                 Reservation.clan_id == resv_in.clan_id,
#                 Reservation.status == ReservationStatus.validated,
#                 Reservation.allow_others == False,
#                 or_(
#                     Reservation.date1 == date1,
#                     Reservation.date1 == date2 if date2 else False,
#                     Reservation.date2 == date1 if date1 else False
#                 )
#             ).first()
            
#             if reserved_valid:
#                 if reserved_valid.date1 == date1:
#                     raise HTTPException(
#                         status_code=400, detail=f"This date {date1} is already reserved in {target_clan.name} clan.")
#                 if date2 != None:
#                     if reserved_valid.date2 == date1:
#                         raise HTTPException(
#                             status_code=400, 
#                             detail=f"This date {date1} is already reserved in {target_clan.name} clan. You can try the second day {date2}."
#                         )
#                     if reserved_valid.date1 == date2:
#                         raise HTTPException(
#                             status_code=400, 
#                             detail=f"This date {date2} is already reserved in {target_clan.name} clan. You can try the first day {date1}."
#                         )
#                 elif date2 == None:
#                     if reserved_valid.date2 == date1:
#                         raise HTTPException(
#                             status_code=400, detail=f"This date {date1} is already reserved in {target_clan.name} clan.")
            
#             # ─────── Validated Mass Wedding Conflict (Cross-Clan) ─────────────
#             mass_conditions = [Reservation.date1 == date1, Reservation.date2 == date1]
#             if date2:
#                 mass_conditions.extend([Reservation.date1 == date2, Reservation.date2 == date2])
            
#             reserved_valid_mass = db.query(Reservation).filter(
#                 Reservation.county_id == current.county_id,
#                 Reservation.clan_id == resv_in.clan_id,
#                 Reservation.status == ReservationStatus.validated,
#                 Reservation.allow_others == True,
#                 or_(*mass_conditions)
#             ).first()
            
#             if reserved_valid_mass:
#                 if reserved_valid_mass.date2 and not date2 and reserved_valid_mass.date2 == date1:
#                     raise HTTPException(
#                         status_code=400, 
#                         detail=f"This date {date1} is already reserved as a second day of a mass wedding in {target_clan.name} clan."
#                     )
#                 if reserved_valid_mass.date2 == date1:
#                     raise HTTPException(
#                         status_code=400, 
#                         detail=f"This date {date1} is already reserved as a second day of a mass wedding in {target_clan.name} clan. You may reserve the second day {date2} if it's still available."
#                     )
#                 if date2 and reserved_valid_mass.date1 == date2:
#                     raise HTTPException(
#                         status_code=400, 
#                         detail=f"This date {date2} is already reserved as a mass wedding in {target_clan.name} clan. You can reserve only the first day {date1}, if it's still available."
#                     )
#                 if reserved_valid_mass.date2 == date1:
#                     raise HTTPException(
#                         status_code=400, 
#                         detail=f"This date {date1} is already reserved as a second mass wedding in {target_clan.name} clan. You may join the wedding on {reserved_valid_mass.date1} if not full."
#                     )
            
#             skip = bool(reserved_valid_mass)
            
#             # ─────── Pending Mass Wedding Join Requests (Cross-Clan) ──────────
#             if not skip:
#                 for d in [date1] + ([date2] if date2 else []):
#                     pending_mass = db.query(Reservation).filter(
#                         Reservation.county_id == current.county_id,
#                         Reservation.clan_id == resv_in.clan_id,
#                         Reservation.status == ReservationStatus.pending_validation,
#                         Reservation.allow_others == True,
#                         or_(Reservation.date1 == d, Reservation.date2 == d)
#                     ).all()
                    
#                     if pending_mass and resv_in.join_to_mass_wedding:
#                         raise HTTPException(
#                             status_code=400,
#                             detail=f"Date {d} is reserved in {target_clan.name} clan but not yet validated. Try again in next {settings.validation_deadline_days} days as max, or choose another date."
#                         )
            
#             # ─────── Pending Solo Wedding Conflicts (Cross-Clan) ──────────────
#             existing_resv = db.query(Reservation).filter(
#                 Reservation.county_id == current.county_id,
#                 Reservation.clan_id == resv_in.clan_id,
#                 Reservation.status == ReservationStatus.pending_validation,
#                 Reservation.allow_others == False,
#                 or_(
#                     Reservation.date1 == date1,
#                     Reservation.date1 == date2 if date2 else False,
#                     Reservation.date2 == date1 if date1 else False
#                 )
#             ).first()
            
#             if existing_resv:
#                 if existing_resv.date1 == date1 or existing_resv.date2 == date1:
#                     raise HTTPException(
#                         status_code=400, 
#                         detail=f"This date {date1} is reserved in {target_clan.name} clan but not yet validated. Please check again in {settings.validation_deadline_days} days."
#                     )
#                 if date2 and existing_resv.date1 == date2:
#                     raise HTTPException(
#                         status_code=400, 
#                         detail=f"This date {date2} is reserved in {target_clan.name} clan but not validated yet. Try booking only {date1}."
#                     )
            
#             # ─────── Cross-Clan Priority Check ────────────────────────────────
#             # Check if there are any same-clan pending reservations that should have priority
#             same_clan_pending = db.query(Reservation).filter(
#                 Reservation.county_id == current.county_id,
#                 Reservation.clan_id == resv_in.clan_id,
#                 Reservation.groom_id.in_(
#                     db.query(User.id).filter(User.clan_id == resv_in.clan_id)
#                 ),
#                 Reservation.status == ReservationStatus.pending_validation,
#                 or_(
#                     Reservation.date1 == date1,
#                     Reservation.date1 == date2 if date2 else False,
#                     Reservation.date2 == date1 if date1 else False,
#                     Reservation.date2 == date2 if date2 else False
#                 )
#             ).first()
            
#             if same_clan_pending and getattr(settings, 'prioritize_same_clan', True):
#                 raise HTTPException(
#                     status_code=400,
#                     detail=f"Same-clan reservations have priority. There is a pending reservation from {target_clan.name} clan members for the selected dates."
#                 )
            
#             # ─────── Capacity Checks (Cross-Clan) ─────────────────────────────
#             for d in [date1] + ([date2] if date2 else []):
#                 n = db.query(Reservation).filter(
#                     Reservation.county_id == current.county_id,
#                     Reservation.clan_id == resv_in.clan_id,
#                     Reservation.status != ReservationStatus.cancelled,
#                     or_(Reservation.date1 == d, Reservation.date2 == d)
#                 ).count()
                
#                 if n >= settings.max_grooms_per_date:
#                     raise HTTPException(
#                         status_code=400, detail=f"Date {d} is fully booked in {target_clan.name} clan.")
                
#                 # Check cross-clan capacity limits
#                 cross_clan_limit = getattr(settings, 'max_cross_clan_per_date', settings.max_grooms_per_date // 2)
#                 cross_clan_count = db.query(Reservation).filter(
#                     Reservation.county_id == current.county_id,
#                     Reservation.clan_id == resv_in.clan_id,
#                     Reservation.status != ReservationStatus.cancelled,
#                     Reservation.groom_id.in_(
#                         db.query(User.id).filter(User.clan_id != resv_in.clan_id)
#                     ),
#                     or_(Reservation.date1 == d, Reservation.date2 == d)
#                 ).count()
                
#                 if cross_clan_count >= cross_clan_limit:
#                     raise HTTPException(
#                         status_code=400, 
#                         detail=f"Cross-clan reservation limit reached for date {d} in {target_clan.name} clan. Currently: {cross_clan_count}/{cross_clan_limit} cross-clan reservations."
#                     )
                
#                 if n > 0 and not resv_in.join_to_mass_wedding and n < settings.max_grooms_per_date:
#                     raise HTTPException(
#                         status_code=400,
#                         detail=f"Date {d} is reserved for mass wedding in {target_clan.name} clan. You can join if you'd like. Currently: {n}/{settings.max_grooms_per_date} grooms."
#                     )
            
#             # Get target clan hall
#             hall = db.query(Hall).filter(Hall.clan_id == resv_in.clan_id).first()
#             if not hall:
#                 raise HTTPException(
#                     status_code=400, detail=f"No hall found for {target_clan.name} clan"
#                 )
            
#             # Cross-clan reservations might require additional approval
#             initial_status = ReservationStatus.pending_validation
#             if getattr(settings, 'require_cross_clan_approval', False):
#                 # You might want to add a new status like 'pending_cross_clan_approval'
#                 pass  # For now, keep the same status

#     else:
#             raise HTTPException(status_code=400, detail="Invalid clan configuration")
    
    
#     expires_at = datetime.utcnow() + timedelta(days=settings.validation_deadline_days)

#     # Get groom information from database
#     groom = db.query(User).filter(User.id == current.id).first()
#     clan = db.query(Clan).filter(Clan.id == resv_in.clan_id).first()
#     if not clan:
#         raise HTTPException(status_code=400, detail="Clan not found")

#     resv = Reservation(
#         groom_id=current.id,
#         clan_id=clan.id,
#         # clan=clan.name,
#         date1=date1,
#         date2=date2,
#         date2_bool=resv_in.date2_bool or False,
#         join_to_mass_wedding=bool(
#             resv_in.join_to_mass_wedding) or bool(resv_in.allow_others),
#         allow_others=bool(resv_in.join_to_mass_wedding) or bool(
#             resv_in.allow_others),
#         status=ReservationStatus.pending_validation,
#         created_at=datetime.utcnow(),
#         expires_at=expires_at,
#         hall_id=hall.id,
#         haia_committee_id=resv_in.haia_committee_id,
#         madaeh_committee_id=resv_in.madaeh_committee_id,

#         # Additional fields from database
#         county_id=clan.county_id if clan else None,
#         first_name=groom.first_name if groom else None,
#         last_name=groom.last_name if groom else None,
#         guardian_name=groom.guardian_name if groom else None,
#         father_name=groom.father_name if groom else None,
#         grandfather_name=groom.grandfather_name if groom else None,
#         birth_date=groom.birth_date if groom else None,
#         birth_address=groom.birth_address if groom else None,
#         home_address=groom.home_address if groom else None,
#         phone_number=groom.phone_number if groom else None,
#         guardian_phone=groom.guardian_phone if groom else None
#     )
#     db.add(resv)
#     db.commit()
#     db.refresh(resv)

#     # 2. Generate PDF immediately after creation

#     pdf_path = generate_wedding_pdf(resv, output_dir="generated_pdfs", db=db)

#     # Update the same reservation with PDF path
#     resv.pdf_url = pdf_path
#     db.commit()
#     db.refresh(resv)

#     return {
#         "message": "Reservation created successfully",
#         "reservation_id": resv.id,
#         "pdf_url": f"/download/{resv.id}"
#     }
#     # return resv


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
