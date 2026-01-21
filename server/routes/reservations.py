# server\routes\reservations.py
"""
Reservation routes for grooms and clan admins.
"""
import logging
from server.models.reservation_clan_admin import ReservationSpecial
from server.schemas.reservations_special import ReservationSpecialStatus
import server.utils.notification_service
import subprocess
from typing import Dict, List, Optional
from sqlalchemy import text
from typing import List, Dict, Optional
from calendar import monthrange
from typing import List, Optional
from sqlalchemy.orm import joinedload
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import date, timedelta, datetime

from server.models.clan import Clan
from server.models.hall import Hall
from server.utils.pdf_generator import generate_wedding_pdf, test_pdf_generation
from server.models.user import User
from ..auth_utils import get_current_user, get_db, require_role
from ..models.user import User, UserRole
from ..models.reservation import PaymentStatus, Reservation, ReservationStatus
from ..models.clan_settings import ClanSettings
from ..schemas.reservation import ReservationCreate, ReservationCreateResponse, ReservationOut
from ..utils.notification_service import NotificationService
from datetime import datetime, date
from sqlalchemy import extract, func

router = APIRouter(
    prefix="/reservations",
    tags=["reservations"]
)

groom_required = require_role([UserRole.groom])
clan_admin_required = require_role([UserRole.clan_admin])

##


############ post new reservation #################################


# Add logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_guardian_completeness(user: User) -> bool:
    """Validate that all required guardian information is present"""
    required_fields = [
        user.guardian_name,
        user.guardian_phone,
        user.guardian_home_address,
        user.guardian_birth_address,
        user.guardian_birth_date
    ]
    return all(field is not None and str(field).strip() for field in required_fields)


def get_mass_wedding_groups_for_date(db: Session, base_filters: List, target_date: date) -> List[Dict]:
    """Get all mass wedding groups for a specific date"""
    mass_weddings = db.query(Reservation).filter(
        *base_filters,
        Reservation.status != ReservationStatus.cancelled,
        or_(Reservation.allow_others == True,
            Reservation.join_to_mass_wedding == True),
        or_(Reservation.date1 == target_date, Reservation.date2 == target_date)
    ).all()

    # Group by wedding leader (first groom who created the mass wedding)
    groups = {}
    for wedding in mass_weddings:
        # Find the earliest reservation for this date combination
        key = f"{wedding.date1}_{wedding.date2}"
        if key not in groups:
            groups[key] = {
                'leader_id': wedding.groom_id,
                'date1': wedding.date1,
                'date2': wedding.date2,
                'reservations': []
            }
        groups[key]['reservations'].append(wedding)

    return list(groups.values())


def check_date_conflicts(db: Session, base_filters: List, date1: date, date2: Optional[date],
                         settings: ClanSettings, clan_name: str) -> None:
    """Comprehensive date conflict checking"""

    dates_to_check = [date1] + ([date2] if date2 else [])

    # Check solo wedding conflicts (validated and pending)
    for check_date in dates_to_check:
        solo_conflicts = db.query(Reservation).filter(
            *base_filters,
            Reservation.status != ReservationStatus.cancelled,
            and_(
                Reservation.allow_others == False,
                Reservation.join_to_mass_wedding == False
            ),
            or_(Reservation.date1 == check_date,
                Reservation.date2 == check_date)
        ).all()

        for solo in solo_conflicts:
            if solo.status == ReservationStatus.validated:
                raise HTTPException(
                    400, f"التاريخ {check_date} محجوز بالفعل")
            elif solo.status == ReservationStatus.pending_validation:
                raise HTTPException(400,
                                    f"التاريخ {check_date} محجوز لكن غير مصدق عليه. \n"
                                    f"تحقق مرة أخرى خلال الايام القادمة\n")


def check_mass_wedding_conflicts(db: Session, base_filters: List, date1: date,
                                 date2: Optional[date], resv_in: ReservationCreate,
                                 settings: ClanSettings, clan_name: str) -> None:
    """Check mass wedding conflicts including two-day scenarios"""

    dates_to_check = [date1] + ([date2] if date2 else [])

    # Get all mass weddings for both dates
    all_mass_weddings = {}
    for check_date in dates_to_check:
        groups = get_mass_wedding_groups_for_date(db, base_filters, check_date)
        all_mass_weddings[check_date] = groups

    if date2:  # Two-day reservation
        day1_groups = all_mass_weddings.get(date1, [])
        day2_groups = all_mass_weddings.get(date2, [])

        # Handle asymmetric mass wedding joining cases
        if day1_groups and not day2_groups:
            # Day 1 has mass wedding, Day 2 is free
            # This is allowed - extends the mass wedding
            pass
        elif not day1_groups and day2_groups:
            # Day 1 is free, Day 2 has mass wedding
            # CRITICAL CASE: Cannot join mass wedding as second day
            if resv_in.join_to_mass_wedding or resv_in.allow_others:
                raise HTTPException(400,
                                    f"لا يمكن الانضمام لعرس جماعي كيوم ثاني. \n"
                                    f"اجعل يومك الأول نفس يوم العرس الجماعي {date2}، \n"
                                    f"أو احجز يوماً واحداً فقط في {date1}")
            else:
                # Solo reservation where day 2 has mass wedding - not allowed
                raise HTTPException(400,
                                    f"التاريخ {date2} محجوز لعرس جماعي. \n"
                                    f"اختر تاريخاً آخر للحجز أو فعل خاصية الانضمام للعرس الجماعي")

        elif day1_groups and day2_groups:
            # Both days have mass weddings
            day1_leaders = {group['leader_id'] for group in day1_groups}
            day2_leaders = {group['leader_id'] for group in day2_groups}

            # If there's no intersection, they're different mass weddings
            if not day1_leaders.intersection(day2_leaders):
                raise HTTPException(400,
                                    f"لا يمكن الحجز في عرسين جماعيين مختلفين. \n"
                                    f"يمكنك الحجز ليوم واحد فقط في {date1} أو {date2}")

            # Same mass wedding group - check if trying to join
            if not resv_in.join_to_mass_wedding and not resv_in.allow_others:
                raise HTTPException(400,
                                    f"التواريخ {date1} و {date2} محجوزة لعرس جماعي. \n"
                                    f"فعل خاصية الانضمام لعرس جماعي")

    # Check individual date mass wedding conflicts
    for check_date in dates_to_check:
        groups = all_mass_weddings.get(check_date, [])

        for group in groups:
            # Check capacity
            current_count = len(group['reservations'])
            if current_count >= settings.max_grooms_per_date:
                raise HTTPException(
                    400, f"التاريخ {check_date} محجوز بالكامل")

            # Check if requesting solo when mass wedding exists
            if not resv_in.join_to_mass_wedding and not resv_in.allow_others:
                raise HTTPException(400,
                                    f"التاريخ {check_date} محجوز لعرس جماعي. \n"
                                    f"فعل خاصية الانضمام إذا كنت ترغب: {current_count}/{settings.max_grooms_per_date} عريس\n")

            # # Check pending mass weddings
            # pending_in_group = any(r.status == ReservationStatus.pending_validation
            #                        for r in group['reservations'])

            # if pending_in_group and resv_in.join_to_mass_wedding:
            #     raise HTTPException(400,
            #                         f"التاريخ {check_date} محجوز لكن غير مصدق عليه. "
            #                         f"جرب مرة أخرى خلال {settings.validation_deadline_days} أيام كحد أقصى")


def check_cross_clan_restrictions(db: Session, base_filters: List, current_user: User,
                                  resv_in: ReservationCreate, target_clan: Optional[Clan],
                                  settings: ClanSettings, date1: date, date2: Optional[date]) -> None:
    """Check all cross-clan related restrictions"""

    is_same_clan = resv_in.clan_id == current_user.clan_id
    if is_same_clan:
        return

    clan_n = db.query(Clan).filter(
        Clan.id == resv_in.clan_id,
    ).first()
    # Cross-clan permission check
    if not getattr(settings, 'allow_cross_clan_reservations', False):
        raise HTTPException(
            400, f"هذه العشيرة ({clan_n.name}) لا تقبل الحجوزات من العشائر الأخرى")

    dates_to_check = [date1] + ([date2] if date2 else [])

    # Cross-clan capacity check
    for check_date in dates_to_check:
        cross_limit = getattr(
            settings, 'max_cross_clan_per_date', settings.max_grooms_per_date // 2)

        cross_count = db.query(Reservation).filter(
            *base_filters,
            Reservation.status != ReservationStatus.cancelled,
            Reservation.groom_id.in_(
                db.query(User.id).filter(User.clan_id != resv_in.clan_id)
            ),
            or_(Reservation.date1 == check_date,
                Reservation.date2 == check_date)
        ).count()

        if cross_count >= cross_limit:
            raise HTTPException(400,
                                f"تم الوصول للحد الأقصى للحجوزات بين العشائر لتاريخ {check_date}: "
                                f"{cross_count}/{cross_limit}")

    # Same-clan priority check
    if getattr(settings, 'prioritize_same_clan', True):
        same_clan_pending = db.query(Reservation).filter(
            *base_filters,
            Reservation.groom_id.in_(
                db.query(User.id).filter(User.clan_id == resv_in.clan_id)
            ),
            Reservation.status == ReservationStatus.pending_validation,
            or_(
                *[or_(Reservation.date1 == d, Reservation.date2 == d) for d in dates_to_check]
            )
        ).first()

        if same_clan_pending:
            raise HTTPException(400,
                                f"حجوزات نفس العشيرة لها الأولوية. يوجد حجز معلق من أعضاء عشيرة {target_clan.name}")


def check_capacity_limits(db: Session, base_filters: List, settings: ClanSettings,
                          date1: date, date2: Optional[date], clan_name: str) -> None:
    """Check capacity limits for all dates"""

    dates_to_check = [date1] + ([date2] if date2 else [])

    for check_date in dates_to_check:
        # Total capacity check
        total_count = db.query(Reservation).filter(
            *base_filters,
            Reservation.status != ReservationStatus.cancelled,
            or_(Reservation.date1 == check_date,
                Reservation.date2 == check_date)
        ).count()

        if total_count >= settings.max_grooms_per_date:
            raise HTTPException(
                400, f"التاريخ {check_date} محجوز بالكامل")


@router.post("", response_model=ReservationCreateResponse, dependencies=[Depends(groom_required)])
def create_reservation(resv_in: ReservationCreate, db: Session = Depends(get_db),
                       current: User = Depends(groom_required)):

    try:
        # Test PDF generation capabilities on first run
        try:
            test_result = test_pdf_generation()
            if not test_result:
                logger.warning("PDF generation test failed, but proceeding...")
        except Exception as e:
            logger.warning(f"PDF generation test error: {e}")

        # BV004-BV005: Check for existing active reservation
        existing_active = db.query(Reservation).filter(
            Reservation.county_id == current.county_id,
            Reservation.groom_id == current.id,
            Reservation.status != ReservationStatus.cancelled
        ).first()

        if existing_active:
            raise HTTPException(400, "لديك بالفعل حجز نشط")

        # BV006: Validate guardian information completeness
        if not validate_guardian_completeness(current):
            raise HTTPException(400, "معلومات ولي الأمر غير مكتملة")

        # BV007-BV009: Determine target clan and validate
        is_same_clan = resv_in.clan_id == current.clan_id
        target_clan = None

        if not is_same_clan:
            target_clan = db.query(Clan).filter(
                Clan.id == resv_in.clan_id).first()
            if not target_clan:
                raise HTTPException(400, "العشيرة المستهدفة غير موجودة")
            if target_clan.county_id != current.county_id:
                raise HTTPException(400, "الحجوزات بين المحافظات غير مسموحة")

        # Get settings
        settings = get_settings_for_clan(db, resv_in.clan_id)
        if not settings:
            raise HTTPException(400,
                                f"إعدادات {'العشيرة' if is_same_clan else 'العشيرة المستهدفة'} غير موجودة")

        # BV010: Check hall availability
        hall = db.query(Hall).filter(Hall.clan_id == resv_in.clan_id).first()
        if not hall:
            clan_name = f" في  {target_clan.name}" if not is_same_clan else ""
            raise HTTPException(400, f"لا توجد قاعة{clan_name}")

        # Parse and validate dates
        date1 = resv_in.date1
        date2 = date1 + timedelta(days=1) if resv_in.date2_bool else None

        # RC009: Validate dates are not in the past
        today = date.today()
        if date1 < today:
            raise HTTPException(400, "لا يمكن الحجز في الماضي")
        if date2 and date2 < today:
            raise HTTPException(
                400, "التاريخ الثاني لا يمكن أن يكون في الماضي")

        # TD001-TD004: Validate two-day reservation month restrictions
        if date2:
            allowed_months = [
                int(m) for m in settings.allowed_months_two_day.split(',')]
            if date1.month not in allowed_months:
                raise HTTPException(
                    400, "الحجوزات ليومين غير مسموحة في هذا الشهر")
            # Check if dates span different months with restrictions
            if date2.month != date1.month and date2.month not in allowed_months:
                raise HTTPException(400, "الشهر الثاني لا يسمح بحجوزات يومين")

        clan_name = f" في  {target_clan.name}" if not is_same_clan else ""

        # Build base query filters
        base_filters = [
            Reservation.county_id == current.county_id,
            Reservation.clan_id == resv_in.clan_id
        ]

        # Use SELECT FOR UPDATE to prevent race conditions
        db.execute(text(
            "SELECT 1 FROM reservations WHERE county_id = :county_id AND clan_id = :clan_id "
            "AND status != 'cancelled' AND (date1 = :date1 OR date2 = :date1 "
            + ("OR date1 = :date2 OR date2 = :date2" if date2 else "") + ") FOR UPDATE"
        ), {
            'county_id': current.county_id,
            'clan_id': resv_in.clan_id,
            'date1': date1,
            'date2': date2
        })

        # Comprehensive conflict checking
        check_date_conflicts(db, base_filters, date1,
                             date2, settings, clan_name)
        check_mass_wedding_conflicts(
            db, base_filters, date1, date2, resv_in, settings, clan_name)
        check_cross_clan_restrictions(
            db, base_filters, current, resv_in, target_clan, settings, date1, date2)
        check_capacity_limits(db, base_filters, settings,
                              date1, date2, clan_name)

        # Get groom and clan info for reservation
        groom = db.query(User).filter(User.id == current.id).first()
        if not is_same_clan:
            clan = target_clan
        else:
            clan = db.query(Clan).filter(Clan.id == current.clan_id).first()

        # Create reservation with all validations passed
        resv = Reservation(
            groom_id=current.id,
            clan_id=resv_in.clan_id,
            date1=date1,
            date2=date2,
            date2_bool=bool(resv_in.date2_bool),
            join_to_mass_wedding=bool(
                resv_in.join_to_mass_wedding or resv_in.allow_others),
            allow_others=bool(
                resv_in.join_to_mass_wedding or resv_in.allow_others),
            status=ReservationStatus.pending_validation,
            payment_status=PaymentStatus.not_paid,
            created_at=datetime.utcnow(),
            hall_id=hall.id,
            haia_committee_id=resv_in.haia_committee_id,
            madaeh_committee_id=resv_in.madaeh_committee_id,
            county_id=clan.county_id,

            # Personal information
            first_name=groom.first_name,
            last_name=groom.last_name,
            father_name=groom.father_name,
            grandfather_name=groom.grandfather_name,
            birth_date=groom.birth_date,
            birth_address=groom.birth_address,
            home_address=groom.home_address,
            phone_number=groom.phone_number,

            # Guardian information
            guardian_name=groom.guardian_name,
            guardian_home_address=groom.guardian_home_address,
            guardian_birth_address=groom.guardian_birth_address,
            guardian_birth_date=groom.guardian_birth_date,
            guardian_phone=groom.guardian_phone
        )

        db.add(resv)
        db.commit()
        db.refresh(resv)
        NotificationService.create_new_reservation_notification(
            db=db,
            reservation=resv
        )

        logger.info(
            f"Successfully created reservation {resv.id} for groom {current.id}")

        return {
            "message": "\nتم إنشاء الحجز بنجاح",
            "reservation_id": resv.id,
            "pdf_url": ""  # PDF will be generated separately
        }

    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_reservation: {e}")
        db.rollback()
        raise HTTPException(500, f"خطأ غير متوقع: {str(e)}")
###


def get_settings_for_clan(db, clan_id):
    return db.query(ClanSettings).filter(ClanSettings.clan_id == clan_id).first()


# get all pending Reservations


@router.get("/pending_reservations", response_model=list[ReservationOut])
def list_clan_reservations(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        Reservation.clan_id == current.clan_id,
        Reservation.status == ReservationStatus.pending_validation

    ).all()

# get all validated Reservations


@router.get("/validated_reservations", response_model=list[ReservationOut])
def list_clan_reservations(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        Reservation.clan_id == current.clan_id,
        Reservation.status == ReservationStatus.validated

    ).all()


# get all pending Reservations
@router.get("/cancled_reservations", response_model=list[ReservationOut])
def list_clan_reservations(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        Reservation.clan_id == current.clan_id,
        Reservation.status == ReservationStatus.cancelled

    ).all()


@router.get("/download/{reservation_id}")
def download_pdf(reservation_id: int):
    pdf_file = f"generated_pdfs/reservation_{reservation_id}.pdf"
    if not os.path.exists(pdf_file):
        raise HTTPException(status_code=404, detail="ملف PDF غير موجود")
    return FileResponse(pdf_file, media_type="application/pdf", filename=f"reservation_{reservation_id}.pdf")
# -----------------------------------------------


# a groom cancel his reservation if is on status of pending validation
@router.post("/{groom_id}/cancel", response_model=ReservationOut, dependencies=[Depends(groom_required)])
def cancel_my_reservation(groom_id: int, db: Session = Depends(get_db), current: User = Depends(groom_required)):
    clan_admin = db.query(User).filter(
        User.clan_id == current.clan_id,
        User.role == UserRole.clan_admin
    ).first()
    resv = db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        Reservation.groom_id == groom_id,
        Reservation.clan_id == current.clan_id,
        Reservation.status != ReservationStatus.cancelled
    ).first()
    if groom_id != current.id:
        raise HTTPException(
            status_code=404, detail="يجب إدخال رقم تعريفك الصحيح لإلغاء حجزك")
    if not resv:
        raise HTTPException(
            status_code=404, detail="الحجز غير موجود")

    if resv.status == ReservationStatus.validated:
        raise HTTPException(
            status_code=400, detail="لا يمكن إلغاء حجز مصدق عليه، اتصل بمدير عشيرتك للمساعدة")

    resv.status = ReservationStatus.cancelled
    db.commit()
    db.refresh(resv)
    NotificationService.create_general_notification(
        db=db,
        user_id=clan_admin.id,
        title="إلغاء حجز",
        message=f"قام العريس {current.first_name} {current.last_name} بإلغاء حجزه.\n   {current.phone_number} رقم الهاتف:",
        reservation_id=resv.id,
        is_groom=False
    )
    return resv


# a clan admin valide a reservation by groom id
@router.post("/{groom_id}/validate", response_model=ReservationOut, dependencies=[Depends(clan_admin_required)])
def validate_reservation(groom_id: int, db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):
    resv_duplicated_check = db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        Reservation.groom_id == groom_id,
        Reservation.clan_id == current.clan_id,
        Reservation.status == ReservationStatus.validated
    ).first()
    if resv_duplicated_check:
        raise HTTPException(
            status_code=404, detail="العريس لديه حجز مصدق عليه موجود بالفعل")

    resv = db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        Reservation.clan_id == current.clan_id,
        Reservation.groom_id == groom_id,
        Reservation.status == ReservationStatus.pending_validation

    ).first()
    if not resv:
        raise HTTPException(
            status_code=404, detail="الحجز غير موجود")

    special_res = db.query(ReservationSpecial).filter(
        ReservationSpecial.county_id == current.county_id,
        ReservationSpecial.clan_id == current.clan_id,
        ReservationSpecial.status == ReservationSpecialStatus.validated,
        or_(ReservationSpecial.date == resv.date1,
            ReservationSpecial.date == resv.date2)
    ).first()

    if special_res:
        raise HTTPException(
            status_code=400, detail="  لا يمكن المصادقة على هذا الحجز هاذ اليوم محجوز من العشيرة"
        )

    resv.status = ReservationStatus.validated
    db.commit()
    db.refresh(resv)
    NotificationService.notify_reservation_validation(
        db=db,
        reservation=resv,
        is_approved=True
    )
    return resv


# a clan admin cancel a reservation by groom id
@router.post("/{groom_id}/cancel_by_clan_admin", response_model=dict, dependencies=[Depends(clan_admin_required)])
def cancel_a_groom_reservation(groom_id: int, db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):

    clan_name = db.query(Clan).filter(
        Clan.id == current.clan_id
    ).first().name
    resv = db.query(Reservation).filter(
        Reservation.county_id == current.county_id,
        Reservation.groom_id == groom_id,
        Reservation.clan_id == current.clan_id,
        Reservation.status != ReservationStatus.cancelled
    ).first()
    if not resv:
        raise HTTPException(
            status_code=404, detail=f"لا يوجد حجز معلق أو مصدق عليه لهذا العريس رقم {groom_id}")

    if resv.status == ReservationStatus.validated:
        valid_cancel = True
    elif resv.status == ReservationStatus.pending_validation:
        valid_cancel = False

    resv.status = ReservationStatus.cancelled
    db.commit()
    db.refresh(resv)
    NotificationService.create_general_notification(
        db=db,
        user_id=resv.groom_id,
        title="إلغاء حجز",
        message=f"قام مدير العشيرة بإلغاء حجزك .   \n {clan_name}  \n  {resv.phone_number}رقم الهاتف:",
        reservation_id=resv.id,
        is_groom=True
    )

    # return resv
    return {
        "message": "تم إلغاء الحجز بنجاح" + (" (كان في حالة مصدق عليه)" if valid_cancel else " (كان في حالة معلق)"),
        "reservation": ReservationOut.from_orm(resv)
    }


@router.delete("/delete_res/{reservation_id}", response_model=dict, dependencies=[Depends(get_current_user)])
def delete_reservation(reservation_id: int, db: Session = Depends(get_db)):
    resv = db.query(Reservation).filter(
        Reservation.id == reservation_id,
    ).first()
    if not resv:
        return {}  # Returns empty dict
    db.delete(resv)
    db.commit()
    return {"message": "تم حذف الحجز بنجاح"}


@router.get("/reservations/my_all_reservations")
def get_my_all_reservations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all reservations for the current groom with joined data"""
    reservations = db.query(Reservation).options(
        joinedload(Reservation.groom).joinedload(
            User.clan),  # Load groom and groom's clan
        joinedload(Reservation.clan),
        joinedload(Reservation.county),
        joinedload(Reservation.hall),
        joinedload(Reservation.haia_committee),
        joinedload(Reservation.madaeh_committee)
    ).filter(Reservation.groom_id == current_user.id).all()

    result = []
    for reservation in reservations:
        reservation_dict = {
            "id": reservation.id,
            "groom_id": reservation.groom_id,
            "clan_id_origin": reservation.groom.clan_id if reservation.groom else None,
            "clan_name_origin": reservation.groom.clan.name if reservation.groom and reservation.groom.clan else None,
            "clan_id": reservation.clan_id,
            "county_id": reservation.county_id,
            "date1": str(reservation.date1) if reservation.date1 else None,
            "date2": str(reservation.date2) if reservation.date2 else None,
            "date2_bool": reservation.date2_bool,
            "allow_others": reservation.allow_others,
            "join_to_mass_wedding": reservation.join_to_mass_wedding,
            "status": reservation.status,
            "created_at": reservation.created_at.isoformat() if reservation.created_at else None,

            # Joined data
            "clan_name": reservation.clan.name if reservation.clan else None,
            "county_name": reservation.county.name if reservation.county else None,
            "hall_name": reservation.hall.name if reservation.hall else None,
            "hall_id": reservation.hall_id,

            # Committee information
            "haia_committee_id": reservation.haia_committee_id,
            "haia_committee_name": reservation.haia_committee.name if reservation.haia_committee else None,
            "madaeh_committee_id": reservation.madaeh_committee_id,
            "madaeh_committee_name": reservation.madaeh_committee.name if reservation.madaeh_committee else None,

            # Personal information
            "pdf_url": reservation.pdf_url,
            "first_name": reservation.first_name,
            "last_name": reservation.last_name,
            "father_name": reservation.father_name,
            "grandfather_name": reservation.grandfather_name,
            "birth_date": str(reservation.birth_date) if reservation.birth_date else None,
            "birth_address": reservation.birth_address,
            "home_address": reservation.home_address,
            "phone_number": reservation.phone_number,
            "payment_valid": reservation.payment_status,

            # Guardian information
            "guardian_name": reservation.guardian_name,
            "guardian_phone": reservation.guardian_phone,
            "guardian_home_address": reservation.guardian_home_address,
            "guardian_birth_address": reservation.guardian_birth_address,
            "guardian_birth_date": str(reservation.guardian_birth_date) if reservation.guardian_birth_date else None,
        }
        result.append(reservation_dict)

    return result


@router.get("/reservations/my_pending_reservation")
def get_my_pending_reservation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pending reservation for the current groom with joined data"""
    reservation = db.query(Reservation).options(
        joinedload(Reservation.groom).joinedload(
            User.clan),
        joinedload(Reservation.clan),
        joinedload(Reservation.county),
        joinedload(Reservation.hall),
        joinedload(Reservation.haia_committee),
        joinedload(Reservation.madaeh_committee)
    ).filter(
        Reservation.groom_id == current_user.id,
        Reservation.status == ReservationStatus.pending_validation
    ).first()

    if not reservation:
        raise HTTPException(
            status_code=404, detail="لا يوجد حجز معلق")

    return {
        "id": reservation.id,
        "groom_id": reservation.groom_id,
        "clan_id_origin": reservation.groom.clan_id if reservation.groom else None,
        "clan_name_origin": reservation.groom.clan.name if reservation.groom and reservation.groom.clan else None,
        "clan_id": reservation.clan_id,
        "county_id": reservation.county_id,
        "date1": str(reservation.date1) if reservation.date1 else None,
        "date2": str(reservation.date2) if reservation.date2 else None,
        "date2_bool": reservation.date2_bool,
        "allow_others": reservation.allow_others,
        "join_to_mass_wedding": reservation.join_to_mass_wedding,
        "status": reservation.status,
        "created_at": reservation.created_at.isoformat() if reservation.created_at else None,

        # Joined data
        "clan_name": reservation.clan.name if reservation.clan else None,
        "county_name": reservation.county.name if reservation.county else None,
        "hall_name": reservation.hall.name if reservation.hall else None,
        "hall_id": reservation.hall_id,

        # Committee information
        "haia_committee_id": reservation.haia_committee_id,
        "haia_committee_name": reservation.haia_committee.name if reservation.haia_committee else None,
        "madaeh_committee_id": reservation.madaeh_committee_id,
        "madaeh_committee_name": reservation.madaeh_committee.name if reservation.madaeh_committee else None,

        # Personal information
        "pdf_url": reservation.pdf_url,
        "first_name": reservation.first_name,
        "last_name": reservation.last_name,
        "father_name": reservation.father_name,
        "grandfather_name": reservation.grandfather_name,
        "birth_date": str(reservation.birth_date) if reservation.birth_date else None,
        "birth_address": reservation.birth_address,
        "home_address": reservation.home_address,
        "phone_number": reservation.phone_number,

        # Guardian information
        "guardian_name": reservation.guardian_name,
        "guardian_phone": reservation.guardian_phone,
        "guardian_home_address": reservation.guardian_home_address,
        "guardian_birth_address": reservation.guardian_birth_address,
        "guardian_birth_date": str(reservation.guardian_birth_date) if reservation.guardian_birth_date else None,
    }


@router.get("/reservations/my_validated_reservation")
def get_my_validated_reservation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get validated reservation for the current groom with joined data"""
    reservation = db.query(Reservation).options(
        joinedload(Reservation.clan),
        joinedload(Reservation.county),
        joinedload(Reservation.hall),
        joinedload(Reservation.haia_committee),
        joinedload(Reservation.madaeh_committee)
    ).filter(
        Reservation.groom_id == current_user.id,
        Reservation.status == ReservationStatus.validated
    ).first()

    if not reservation:
        raise HTTPException(
            status_code=404, detail="لا يوجد حجز مؤكد")

    return {
        "id": reservation.id,
        "groom_id": reservation.groom_id,
        "clan_id": reservation.clan_id,
        "county_id": reservation.county_id,
        "date1": str(reservation.date1) if reservation.date1 else None,
        "date2": str(reservation.date2) if reservation.date2 else None,
        "date2_bool": reservation.date2_bool,
        "allow_others": reservation.allow_others,
        "join_to_mass_wedding": reservation.join_to_mass_wedding,
        "status": reservation.status,
        "created_at": reservation.created_at.isoformat() if reservation.created_at else None,

        # Joined data
        "clan_name": reservation.clan.name if reservation.clan else None,
        "county_name": reservation.county.name if reservation.county else None,
        "hall_name": reservation.hall.name if reservation.hall else None,
        "hall_id": reservation.hall_id,

        # Committee information
        "haia_committee_id": reservation.haia_committee_id,
        "haia_committee_name": reservation.haia_committee.name if reservation.haia_committee else None,
        "madaeh_committee_id": reservation.madaeh_committee_id,
        "madaeh_committee_name": reservation.madaeh_committee.name if reservation.madaeh_committee else None,

        # Personal information
        "pdf_url": reservation.pdf_url,
        "first_name": reservation.first_name,
        "last_name": reservation.last_name,
        "father_name": reservation.father_name,
        "grandfather_name": reservation.grandfather_name,
        "birth_date": str(reservation.birth_date) if reservation.birth_date else None,
        "birth_address": reservation.birth_address,
        "home_address": reservation.home_address,
        "phone_number": reservation.phone_number,
        "payment_valid": reservation.payment_status,

        # Guardian information
        "guardian_name": reservation.guardian_name,
        "guardian_phone": reservation.guardian_phone,
        "guardian_home_address": reservation.guardian_home_address,
        "guardian_birth_address": reservation.guardian_birth_address,
        "guardian_birth_date": str(reservation.guardian_birth_date) if reservation.guardian_birth_date else None,
    }


@router.get("/reservations/my_cancelled_reservation")
def get_my_cancelled_reservations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all cancelled reservations for the current groom with joined data"""
    reservations = db.query(Reservation).options(
        joinedload(Reservation.clan),
        joinedload(Reservation.county),
        joinedload(Reservation.hall),
        joinedload(Reservation.haia_committee),
        joinedload(Reservation.madaeh_committee)
    ).filter(
        Reservation.groom_id == current_user.id,
        Reservation.status == ReservationStatus.cancelled
    ).all()

    result = []
    for reservation in reservations:
        reservation_dict = {
            "id": reservation.id,
            "groom_id": reservation.groom_id,
            "clan_id": reservation.clan_id,
            "county_id": reservation.county_id,
            "date1": str(reservation.date1) if reservation.date1 else None,
            "date2": str(reservation.date2) if reservation.date2 else None,
            "date2_bool": reservation.date2_bool,
            "allow_others": reservation.allow_others,
            "join_to_mass_wedding": reservation.join_to_mass_wedding,
            "status": reservation.status,
            "created_at": reservation.created_at.isoformat() if reservation.created_at else None,

            # Joined data
            "clan_name": reservation.clan.name if reservation.clan else None,
            "county_name": reservation.county.name if reservation.county else None,
            "hall_name": reservation.hall.name if reservation.hall else None,
            "hall_id": reservation.hall_id,

            # Committee information
            "haia_committee_id": reservation.haia_committee_id,
            "haia_committee_name": reservation.haia_committee.name if reservation.haia_committee else None,
            "madaeh_committee_id": reservation.madaeh_committee_id,
            "madaeh_committee_name": reservation.madaeh_committee.name if reservation.madaeh_committee else None,

            # Personal information
            "pdf_url": reservation.pdf_url,
            "first_name": reservation.first_name,
            "last_name": reservation.last_name,
            "father_name": reservation.father_name,
            "grandfather_name": reservation.grandfather_name,
            "birth_date": str(reservation.birth_date) if reservation.birth_date else None,
            "birth_address": reservation.birth_address,
            "home_address": reservation.home_address,
            "phone_number": reservation.phone_number,
            "payment_valid": reservation.payment_status,

            # Guardian information
            "guardian_name": reservation.guardian_name,
            "guardian_phone": reservation.guardian_phone,
            "guardian_home_address": reservation.guardian_home_address,
            "guardian_birth_address": reservation.guardian_birth_address,
            "guardian_birth_date": str(reservation.guardian_birth_date) if reservation.guardian_birth_date else None,
        }
        result.append(reservation_dict)

    return result

# Update the cancel reservation endpoint to use reservation ID instead of groom ID


@router.post("/reservations/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a reservation by its ID"""
    reservation = db.query(Reservation).filter(
        Reservation.id == reservation_id,
        Reservation.groom_id == current_user.id
    ).first()

    if not reservation:
        raise HTTPException(status_code=404, detail="الحجز غير موجود")

    if reservation.status == ReservationStatus.cancelled:
        raise HTTPException(
            status_code=400, detail="الحجز ملغي بالفعل")

    if reservation.status == ReservationStatus.validated:
        raise HTTPException(
            status_code=400, detail="لا يمكن إلغاء حجز مؤكد")

    reservation.status = ReservationStatus.cancelled
    db.commit()

    return {"message": "تم إلغاء الحجز بنجاح"}

# Also update the admin reservation endpoints with joined data


@router.get("/reservations/all_reservations")
def get_all_reservations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all reservations for the current clan admin's clan with joined data"""
    reservations = db.query(Reservation).options(
        joinedload(Reservation.clan),
        joinedload(Reservation.county),
        joinedload(Reservation.hall),
        joinedload(Reservation.haia_committee),
        joinedload(Reservation.madaeh_committee),
        joinedload(Reservation.groom)
    ).filter(Reservation.clan_id == current_user.clan_id).all()

    result = []
    for reservation in reservations:
        reservation_dict = {
            "id": reservation.id,
            "groom_id": reservation.groom_id,
            "clan_id": reservation.clan_id,
            "county_id": reservation.county_id,
            "date1": str(reservation.date1) if reservation.date1 else None,
            "date2": str(reservation.date2) if reservation.date2 else None,
            "date2_bool": reservation.date2_bool,
            "allow_others": reservation.allow_others,
            "join_to_mass_wedding": reservation.join_to_mass_wedding,
            "status": reservation.status,
            "created_at": reservation.created_at.isoformat() if reservation.created_at else None,

            # Joined data
            "clan_name": reservation.clan.name if reservation.clan else None,
            "county_name": reservation.county.name if reservation.county else None,
            "hall_name": reservation.hall.name if reservation.hall else None,
            "hall_id": reservation.hall_id,

            # Committee information
            "haia_committee_id": reservation.haia_committee_id,
            "haia_committee_name": reservation.haia_committee.name if reservation.haia_committee else None,
            "madaeh_committee_id": reservation.madaeh_committee_id,
            "madaeh_committee_name": reservation.madaeh_committee.name if reservation.madaeh_committee else None,

            # Groom information
            "groom_first_name": reservation.groom.first_name if reservation.groom else None,
            "groom_last_name": reservation.groom.last_name if reservation.groom else None,
            "groom_phone_number": reservation.groom.phone_number if reservation.groom else None,

            # Personal information from reservation
            "pdf_url": reservation.pdf_url,
            "first_name": reservation.first_name,
            "last_name": reservation.last_name,
            "father_name": reservation.father_name,
            "grandfather_name": reservation.grandfather_name,
            "birth_date": str(reservation.birth_date) if reservation.birth_date else None,
            "birth_address": reservation.birth_address,
            "home_address": reservation.home_address,
            "phone_number": reservation.phone_number,
            "payment_valid": reservation.payment_status,

            # Guardian information
            "guardian_name": reservation.guardian_name,
            "guardian_phone": reservation.guardian_phone,
            "guardian_home_address": reservation.guardian_home_address,
            "guardian_birth_address": reservation.guardian_birth_address,
            "guardian_birth_date": str(reservation.guardian_birth_date) if reservation.guardian_birth_date else None,
        }
        result.append(reservation_dict)

    return result


@router.get("/clan_admin/all_reservations")
def get_all_reservations_for_clan_admin(
    current_user: User = Depends(clan_admin_required),
    db: Session = Depends(get_db)
):
    """Get all reservations for clan admin with explicit role check"""
    if current_user.role != UserRole.clan_admin:
        raise HTTPException(
            status_code=403,
            detail="هذه الصفحة متاحة فقط لمديري العشائر"
        )

    reservations = db.query(Reservation).options(
        joinedload(Reservation.clan),
        joinedload(Reservation.county),
        joinedload(Reservation.hall),
        joinedload(Reservation.haia_committee),
        joinedload(Reservation.madaeh_committee),
        joinedload(Reservation.groom)
    ).filter(
        Reservation.clan_id == current_user.clan_id,
        Reservation.county_id == current_user.county_id
    ).all()

    result = []
    for reservation in reservations:
        reservation_dict = {
            "id": reservation.id,
            "groom_id": reservation.groom_id,
            "clan_id": reservation.clan_id,
            "county_id": reservation.county_id,
            "date1": str(reservation.date1) if reservation.date1 else None,
            "date2": str(reservation.date2) if reservation.date2 else None,
            "date2_bool": reservation.date2_bool,
            "allow_others": reservation.allow_others,
            "join_to_mass_wedding": reservation.join_to_mass_wedding,
            "status": reservation.status,
            "payment_valid": reservation.payment_status,
            "created_at": reservation.created_at.isoformat() if reservation.created_at else None,

            # Joined data
            "clan_name": reservation.clan.name if reservation.clan else None,
            "county_name": reservation.county.name if reservation.county else None,
            "hall_name": reservation.hall.name if reservation.hall else None,
            "hall_id": reservation.hall_id,

            # Committee information
            "haia_committee_id": reservation.haia_committee_id,
            "haia_committee_name": reservation.haia_committee.name if reservation.haia_committee else None,
            "madaeh_committee_id": reservation.madaeh_committee_id,
            "madaeh_committee_name": reservation.madaeh_committee.name if reservation.madaeh_committee else None,

            # Personal information
            "pdf_url": reservation.pdf_url,
            "first_name": reservation.first_name,
            "last_name": reservation.last_name,
            "father_name": reservation.father_name,
            "grandfather_name": reservation.grandfather_name,
            "birth_date": str(reservation.birth_date) if reservation.birth_date else None,
            "birth_address": reservation.birth_address,
            "home_address": reservation.home_address,
            "phone_number": reservation.phone_number,

            # Guardian information
            "guardian_name": reservation.guardian_name,
            "guardian_phone": reservation.guardian_phone,
            "guardian_home_address": reservation.guardian_home_address,
            "guardian_birth_address": reservation.guardian_birth_address,
            "guardian_birth_date": str(reservation.guardian_birth_date) if reservation.guardian_birth_date else None,
        }
        result.append(reservation_dict)

    return result
##########


@router.get("/validated-dates/{clan_id}")
def get_validated_dates(
    clan_id: int,
    db: Session = Depends(get_db),
):
    """
    Get all dates with validated reservations for a specific clan
    """
    try:
        # Validate clan exists
        clan = db.query(Clan).filter(Clan.id == clan_id).first()
        if not clan:
            raise HTTPException(status_code=404, detail="العشيرة غير موجودة")

        # Get clan settings
        settings = get_settings_for_clan(db, clan_id)
        if not settings:
            raise HTTPException(
                status_code=404, detail="إعدادات العشيرة غير موجودة")

        # Get all validated reservations for the clan
        reservations = db.query(Reservation).filter(
            Reservation.clan_id == clan_id,
            Reservation.status == ReservationStatus.validated
        ).all()

        # Return the dates column only
        for res in reservations:
            res.date1 = str(res.date1) if res.date1 else None
            res.date2 = str(res.date2) if res.date2 else None

        return reservations

    except Exception as e:
        print(f"Error in get_validated_dates: {e}")
        raise HTTPException(
            status_code=500, detail=f"خطأ في جلب التواريخ المؤكدة: {str(e)}")


@router.get("/pending-dates/{clan_id}")
def get_pending_dates(
    clan_id: int,
    db: Session = Depends(get_db),
):
    """
    Get all dates with pending_validation reservations for a specific clan
    """
    try:
        # Validate clan exists
        clan = db.query(Clan).filter(Clan.id == clan_id).first()
        if not clan:
            raise HTTPException(status_code=404, detail="العشيرة غير موجودة")

        # Get clan settings
        settings = get_settings_for_clan(db, clan_id)
        if not settings:
            raise HTTPException(
                status_code=404, detail="إعدادات العشيرة غير موجودة")

        # Get all pending_validation reservations for the clan
        reservations = db.query(Reservation).filter(
            Reservation.clan_id == clan_id,
            Reservation.status == ReservationStatus.pending_validation
        ).all()

        # Return the dates column only
        for res in reservations:
            res.date1 = str(res.date1) if res.date1 else None
            res.date2 = str(res.date2) if res.date2 else None

        return reservations

    except Exception as e:
        print(f"Error in get_pending_dates: {e}")
        raise HTTPException(
            status_code=500, detail=f"خطأ في جلب التواريخ المعلقة: {str(e)}")

# routers for the statistics section


# For a specific clan - by day
@router.get("/valid_reservations_today")
def get_valid_reservations_today(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Get validated reservations for today for a specific clan
    """
    try:
        today = date.today()
        reservations = db.query(Reservation).filter(
            Reservation.county_id == current.county_id,
            Reservation.clan_id == current.clan_id,
            Reservation.status == ReservationStatus.validated,
            func.date(Reservation.date1) == today
        ).all()

        return {
            "count": len(reservations),
            "reservations": [
                {
                    "id": res.id,
                    "date1": res.date1.isoformat() if res.date1 else None
                }
                for res in reservations
            ],
            "date": today.isoformat(),
            "clan_id": current.clan_id
        }
    except Exception as e:
        print(f"Error in get_valid_reservations_today: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في جلب عدد الحجوزات المؤكدة لليوم: {str(e)}"
        )


# For a specific clan - by month
@router.get("/valid_reservations_month")
def get_valid_reservations_month(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Get validated reservations for current month for a specific clan
    """
    try:
        now = datetime.now()
        current_month = now.month
        current_year = now.year

        reservations = db.query(Reservation).filter(
            Reservation.county_id == current.county_id,
            Reservation.clan_id == current.clan_id,
            Reservation.status == ReservationStatus.validated,
            extract('month', Reservation.date1) == current_month,
            extract('year', Reservation.date1) == current_year
        ).all()

        return {
            "count": len(reservations),
            "reservations": [
                {
                    "id": res.id,
                    "date1": res.date1.isoformat() if res.date1 else None
                }
                for res in reservations
            ],
            "month": current_month,
            "year": current_year,
            "clan_id": current.clan_id
        }
    except Exception as e:
        print(f"Error in get_valid_reservations_month: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في جلب عدد الحجوزات المؤكدة للشهر: {str(e)}"
        )

#########################
# For a specific clan - by year


@router.get("/valid_reservations_year")
def get_valid_reservations_year(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Get validated reservations for current year for a specific clan
    """
    try:
        current_year = datetime.now().year

        reservations = db.query(Reservation).filter(
            Reservation.county_id == current.county_id,
            Reservation.clan_id == current.clan_id,
            Reservation.status == ReservationStatus.validated,
            extract('year', Reservation.date1) == current_year
        ).all()

        return {
            "count": len(reservations),
            "reservations": [
                {
                    "id": res.id,
                    "date1": res.date1.isoformat() if res.date1 else None
                }
                for res in reservations
            ],
            "year": current_year,
            "clan_id": current.clan_id
        }
    except Exception as e:
        print(f"Error in get_valid_reservations_year: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في جلب عدد الحجوزات المؤكدة للسنة: {str(e)}"
        )


# For entire county - by day
@router.get("/valid_reservations_today_county")
def get_valid_reservations_today_county(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Get validated reservations for today for all clans in the county
    """
    try:
        today = date.today()
        reservations = db.query(Reservation).filter(
            Reservation.county_id == current.county_id,
            Reservation.status == ReservationStatus.validated,
            func.date(Reservation.date1) == today
        ).all()

        return {
            "count": len(reservations),
            "reservations": [
                {
                    "id": res.id,
                    "date1": res.date1.isoformat() if res.date1 else None
                }
                for res in reservations
            ],
            "date": today.isoformat()
        }
    except Exception as e:
        print(f"Error in get_valid_reservations_today_county: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في جلب عدد الحجوزات المؤكدة لليوم: {str(e)}"
        )


# For entire county - by month
@router.get("/valid_reservations_month_county")
def get_valid_reservations_month_county(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Get validated reservations for current month for all clans in the county
    """
    try:
        now = datetime.now()
        current_month = now.month
        current_year = now.year

        reservations = db.query(Reservation).filter(
            Reservation.county_id == current.county_id,
            Reservation.status == ReservationStatus.validated,
            extract('month', Reservation.date1) == current_month,
            extract('year', Reservation.date1) == current_year
        ).all()

        return {
            "count": len(reservations),
            "reservations": [
                {
                    "id": res.id,
                    "date1": res.date1.isoformat() if res.date1 else None
                }
                for res in reservations
            ],
            "month": current_month,
            "year": current_year
        }
    except Exception as e:
        print(f"Error in get_valid_reservations_month_county: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في جلب عدد الحجوزات المؤكدة للشهر: {str(e)}"
        )


# For entire county - by year
@router.get("/valid_reservations_year_county")
def get_valid_reservations_year_county(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Get validated reservations for current year for all clans in the county
    """
    try:
        current_year = datetime.now().year

        reservations = db.query(Reservation).filter(
            Reservation.county_id == current.county_id,
            Reservation.status == ReservationStatus.validated,
            extract('year', Reservation.date1) == current_year
        ).all()

        return {
            "count": len(reservations),
            "reservations": [
                {
                    "id": res.id,
                    "date1": res.date1.isoformat() if res.date1 else None
                }
                for res in reservations
            ],
            "year": current_year
        }
    except Exception as e:
        print(f"Error in get_valid_reservations_year_county: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في جلب عدد الحجوزات المؤكدة للسنة: {str(e)}"
        )
