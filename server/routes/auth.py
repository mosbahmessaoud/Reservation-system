
# server\routes\auth.py
from server.auth_utils import verify_access_password
from server.models.reservation import Reservation, ReservationStatus
from server.schemas.user import AccessPasswordVerify
from tokenize import String
from fastapi import APIRouter, Body, Depends, HTTPException, logger, status
from platformdirs import user_config_dir
from pydantic import BaseModel
import sqlalchemy
import sqlalchemy.orm
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from server.models.user import User, UserRole, UserStatus
from server.models.clan import Clan
from server.models.county import County
from server.schemas.user import UpdateGroomRequest, UserCreate, UserOut
from server.schemas.auth import LoginRequest, RegisterResponse, Token
from server.utils.otp_utils import send_otp_to_user_by_twilo, generate_otp_code, verify_otp
from server.utils.phone_utils import validate_algerian_number, validate_number_phone, validate_number_phone_of_guardian
from sqlalchemy import or_
from .. import auth_utils
from ..db import get_db


import logging
import traceback

# At the top of your file
logger = logging.getLogger(__name__)


router = APIRouter(prefix="/auth", tags=["auth"])

super_admin_required = auth_utils.require_role([UserRole.super_admin])
clan_admin_required = auth_utils.require_role([UserRole.clan_admin])
groom_required = auth_utils.require_role([UserRole.groom])

# get role of the user


@router.get("/get_role", response_model=UserOut)
def get_user_role(
    db: Session = Depends(get_db),
    current: User = Depends(auth_utils.get_current_user)
):
    user_info = db.query(User).filter(User.id == current.id).first()
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المستخدم غير موجود"
        )

    return user_info


@router.delete("/delet_user/{phone__number}")
def delet_user(phone__number: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.phone_number == phone__number
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المستخدم غير موجود"
        )
    db.delete(user)
    db.commit()

    return {'message': f'تم حذف المستخدم صاحب رقم الهاتف {phone__number} بنجاح'}


@router.get("/me")
def get_current_user_info(
    db: Session = Depends(get_db),
    current: User = Depends(auth_utils.get_current_user)
):
    user = db.query(User).options(
        joinedload(User.clan),
        joinedload(User.county)
    ).filter(User.id == current.id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المستخدم غير موجود"
        )

    user = {
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

        "access_pages_password_hash": user.access_pages_password_hash,
    }

    return user


@router.post("/login", response_model=Token)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):

    user = auth_utils.authenticate_user(
        db, request.phone_number, request.password
    )

    if not user:
        print(f"❌ Authentication failed for {request.phone_number}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="رقم الهاتف أو كلمة المرور غير صحيحة"
        )
    print(f"✅ Authentication successful for {request.phone_number}")

    if not user.phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="رقم الهاتف غير مؤكد"
        )

    # Check if user status is active
    if user.status != UserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="حسابك غير نشط. يرجى مراجعة مدير العشيرة للحصول على المساعدة."
        )

    if not user.access_pages_password_hash and user.role == UserRole.groom:
        access_pages_password = "تعشيرت"
        # access_pages_password = "تعشيرت"+user.phone_number
        hashed_access_pages_password = auth_utils.get_password_hash(
            access_pages_password)
        user.access_pages_password_hash = hashed_access_pages_password
        db.commit()
        db.refresh(user)

    access_token = auth_utils.create_access_token(
        data={"sub": str(user.id), "role": user.role}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


def has_reservation(db: Session, groom_id: int) -> bool:
    """Check if the groom has any valid reservations."""
    now = datetime.utcnow()
    reservations = db.query(Reservation).filter(
        Reservation.groom_id == groom_id,
        Reservation.status != ReservationStatus.cancelled,
        Reservation.date1 >= now,
    ).all()
    return len(reservations) > 0


class PhoneGroom(BaseModel):
    phone_number: str
# check for the phone groom existing or not router


@router.post("/check_groom_phone")
def check_groom_phone_existing(
    data: PhoneGroom,
    db: Session = Depends(get_db),
):

    existing_user = db.query(User).filter(
        sqlalchemy.or_(User.guardian_phone == data.phone_number,
                       User.phone_number == data.phone_number),
    ).first()

    if existing_user and has_reservation(db, existing_user.id):
        return {"exists": True, "message": ". رقم هاتف العريس موجود بالفعل ويوجد حجز فيه\n اذا نسيت كلمة المرور، يرجى استخدام خاصية «نسيت كلمة المرور»  "}
    else:
        return {"exists": False, "message": "رقم هاتف العريس غير موجود."}


class PhoneGuardian(BaseModel):
    phone_number: str
# check for the phone guardian existing or not router


@router.post("/check_guardian_phone")
def check_guardian_phone_existing(
    data: PhoneGuardian,
    db: Session = Depends(get_db),
):

    existing_user = db.query(User).filter(

        sqlalchemy.or_(User.guardian_phone == data.phone_number,
                       User.phone_number == data.phone_number),

    ).first()

    if existing_user and has_reservation(db, existing_user.id):
        return {"exists": True, "message": "رقم هاتف الولي موجود بالفعل. ويوجد حجز فيه\n اذا نسيت كلمة المرور، يرجى استخدام خاصية «نسيت كلمة المرور»."}
    else:
        return {"exists": False, "message": "رقم هاتف الولي غير موجود."}


# @router.post("/register/groom", response_model=RegisterResponse)
# def register_groom(user_in: UserCreate, db: Session = Depends(get_db)):
#     if user_in.role != UserRole.groom:
#         raise HTTPException(
#             status_code=400, detail="يمكن للعرسان فقط التسجيل بأنفسهم")

#  # Check for existing user with this phone number
#     existing_user = db.query(User).filter(
#         or_(User.phone_number == user_in.phone_number,
#             User.guardian_phone == user_in.phone_number),
#     ).first()

#     # if existing_user:
#     # if existing_user.phone_verified:
#     #     # Phone is verified, don't allow registration
#     #     raise HTTPException(
#     #         status_code=400, detail=("رقم هاتف العريس موجود بالفعل ومؤكد\n"
#     #                                  "  اذا نسيت كلمة المرور يرجى إعادة تعيين كلمة المرور عبر خاصية «نسيت كلمة المرور». "
#     #                                  ))
#     if existing_user:
#         if has_reservation(db, existing_user.id):
#             raise HTTPException(
#                 status_code=400,
#                 detail=(
#                     f"رقم هاتف العريس "
#                     "موجود بالفعل، ويوجد حجز فيه .\n"
#                     "يرجى إعادة تعيين كلمة المرور عبر خاصية «نسيت كلمة المرور»."
#                 )
#             )
#         else:
#             # Phone is not verified, delete the old unverified user
#             db.delete(existing_user)
#             db.commit()

#     existing_user_by_guardian_phone = db.query(User).filter(
#         sqlalchemy.or_(User.guardian_phone == user_in.guardian_phone,
#                        User.phone_number == user_in.guardian_phone),

#     ).first()

#     # if existing_user_by_guardian_phone:
#     # if existing_user_by_guardian_phone.phone_verified:
#     #     # Phone is verified, don't allow registration
#     #     raise HTTPException(
#     #         status_code=400, detail=("رقم هاتف الولي موجود بالفعل ومؤكد\n"
#     #                                  "  اذا نسيت كلمة المرور يرجى إعادة تعيين كلمة المرور عبر خاصية «نسيت كلمة المرور». "
#     #                                  ))
#     if existing_user_by_guardian_phone:
#         if has_reservation(db, existing_user_by_guardian_phone.id):
#             raise HTTPException(
#                 status_code=400,
#                 detail=(
#                     f"رقم هاتف الولي  "
#                     "مستخدم بالفعل، ويوجد حجز فيه.\n"
#                     "يرجى إعادة تعيين كلمة المرور عبر خاصية «نسيت كلمة المرور»."
#                 )
#             )
#         else:
#             # Phone is not verified, delete the old unverified user
#             db.delete(existing_user_by_guardian_phone)
#             db.commit()

#     clan = db.query(Clan).filter(Clan.id == user_in.clan_id).first()
#     if not clan:
#         raise HTTPException(
#             status_code=404, detail=f"معرف العشيرة {user_in.clan_id} غير موجود.")

#     county = db.query(County).filter(County.id == user_in.county_id).first()
#     if not county:
#         raise HTTPException(
#             status_code=404, detail=f"معرف المقاطعة {user_in.county_id} غير موجود.")

#     if clan.county_id != county.id:
#         raise HTTPException(
#             status_code=404, detail="العشيرة لا تنتمي إلى هذه المقاطعة.")

#     access_pages_password = "تعشيرت"
#     # access_pages_password = "تعشيرت"+user_in.phone_number
#     hashed_access_pages_password = auth_utils.get_password_hash(
#         access_pages_password)
#     hashed_password = auth_utils.get_password_hash(user_in.password)
#     otp_code = generate_otp_code()

#     # guardian_phone = validate_algerian_number(user_in.guardian_phone)
#     validate_number_phone(user_in.phone_number)
#     validate_number_phone_of_guardian(user_in.guardian_phone)

#     user = User(
#         phone_number=user_in.phone_number,
#         password_hash=hashed_password,
#         access_pages_password_hash=hashed_access_pages_password,
#         role=UserRole.groom,
#         first_name=user_in.first_name,
#         last_name=user_in.last_name,
#         father_name=user_in.father_name,
#         grandfather_name=user_in.grandfather_name,
#         birth_date=user_in.birth_date,
#         birth_address=user_in.birth_address,
#         home_address=user_in.home_address,
#         clan_id=user_in.clan_id,
#         county_id=user_in.county_id,
#         guardian_name=user_in.guardian_name,
#         guardian_phone=user_in.guardian_phone,
#         guardian_home_address=user_in.guardian_home_address,
#         guardian_birth_address=user_in.guardian_birth_address,
#         guardian_birth_date=user_in.guardian_birth_date,
#         guardian_relation=user_in.guardian_relation,
#         otp_code=otp_code,
#         sms_to_groom_phone=user_in.sms_to_groom_phone,
#         otp_expiration=datetime.utcnow() + timedelta(hours=4),
#         created_at=datetime.utcnow(),
#         status=UserStatus.active,
#     )

#     db.add(user)
#     db.commit()
#     db.refresh(user)
#     # Send OTP
#     try:
#         if user_in.sms_to_groom_phone == True:
#             send_otp_to_user_by_twilo(user.phone_number, otp_code)
#         else:
#             send_otp_to_user_by_twilo(user.guardian_phone, otp_code)
#     except ValueError as e:
#         # If SMS fails, still keep user but notify
#         logger.error(f"SMS failed for {user.phone_number}: {e}")
#         db.delete(user)
#         db.commit()
#         return {
#             "message": " فشل إرسال الرمز",
#             "error": str(e)
#         }

#     return {
#         "message": "تم إنشاء الحساب. تحقق من هاتفك",
#         "user": user
#     }


@router.post("/register/groom", response_model=RegisterResponse)
def register_groom(user_in: UserCreate, db: Session = Depends(get_db)):
    try:
        logger.info(
            f"🔵 Starting registration for phone: {user_in.phone_number}")

        if user_in.role != UserRole.groom:
            raise HTTPException(
                status_code=400, detail="يمكن للعرسان فقط التسجيل بأنفسهم")

        logger.info(
            f"🔵 Checking existing user with phone: {user_in.phone_number}")
        existing_user = db.query(User).filter(
            or_(User.phone_number == user_in.phone_number,
                User.guardian_phone == user_in.phone_number),
        ).first()

        if existing_user:
            logger.info(f"🟡 Found existing user: {existing_user.id}")
            if has_reservation(db, existing_user.id):
                logger.warning(
                    f"⚠️ User has reservation, blocking registration")
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"رقم هاتف العريس "
                        "موجود بالفعل، ويوجد حجز فيه .\n"
                        "يرجى إعادة تعيين كلمة المرور عبر خاصية «نسيت كلمة المرور»."
                    )
                )
            else:
                logger.info(
                    f"🔵 Deleting old unverified user: {existing_user.id}")
                db.delete(existing_user)
                db.commit()

        logger.info(f"🔵 Checking guardian phone: {user_in.guardian_phone}")
        existing_user_by_guardian_phone = db.query(User).filter(
            sqlalchemy.or_(User.guardian_phone == user_in.guardian_phone,
                           User.phone_number == user_in.guardian_phone),
        ).first()

        if existing_user_by_guardian_phone:
            logger.info(
                f"🟡 Found existing guardian user: {existing_user_by_guardian_phone.id}")
            if has_reservation(db, existing_user_by_guardian_phone.id):
                logger.warning(
                    f"⚠️ Guardian user has reservation, blocking registration")
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"رقم هاتف الولي  "
                        "مستخدم بالفعل، ويوجد حجز فيه.\n"
                        "يرجى إعادة تعيين كلمة المرور عبر خاصية «نسيت كلمة المرور»."
                    )
                )
            else:
                logger.info(
                    f"🔵 Deleting old guardian user: {existing_user_by_guardian_phone.id}")
                db.delete(existing_user_by_guardian_phone)
                db.commit()

        logger.info(f"🔵 Validating clan_id: {user_in.clan_id}")
        clan = db.query(Clan).filter(Clan.id == user_in.clan_id).first()
        if not clan:
            logger.error(f"❌ Clan not found: {user_in.clan_id}")
            raise HTTPException(
                status_code=404, detail=f"معرف العشيرة {user_in.clan_id} غير موجود.")

        logger.info(f"🔵 Validating county_id: {user_in.county_id}")
        county = db.query(County).filter(
            County.id == user_in.county_id).first()
        if not county:
            logger.error(f"❌ County not found: {user_in.county_id}")
            raise HTTPException(
                status_code=404, detail=f"معرف المقاطعة {user_in.county_id} غير موجود.")

        if clan.county_id != county.id:
            logger.error(
                f"❌ Clan {clan.id} doesn't belong to county {county.id}")
            raise HTTPException(
                status_code=404, detail="العشيرة لا تنتمي إلى هذه المقاطعة.")

        logger.info(f"🔵 Hashing passwords...")
        access_pages_password = "تعشيرت"
        hashed_access_pages_password = auth_utils.get_password_hash(
            access_pages_password)
        hashed_password = auth_utils.get_password_hash(user_in.password)
        otp_code = generate_otp_code()

        logger.info(f"🔵 Validating phone numbers...")
        validate_number_phone(user_in.phone_number)
        validate_number_phone_of_guardian(user_in.guardian_phone)

        logger.info(f"🔵 Creating user object...")
        user = User(
            phone_number=user_in.phone_number,
            password_hash=hashed_password,
            access_pages_password_hash=hashed_access_pages_password,
            role=UserRole.groom,
            first_name=user_in.first_name,
            last_name=user_in.last_name,
            father_name=user_in.father_name,
            grandfather_name=user_in.grandfather_name,
            birth_date=user_in.birth_date,
            birth_address=user_in.birth_address,
            home_address=user_in.home_address,
            clan_id=user_in.clan_id,
            county_id=user_in.county_id,
            guardian_name=user_in.guardian_name,
            guardian_phone=user_in.guardian_phone,
            guardian_home_address=user_in.guardian_home_address,
            guardian_birth_address=user_in.guardian_birth_address,
            guardian_birth_date=user_in.guardian_birth_date,
            guardian_relation=user_in.guardian_relation,
            otp_code=otp_code,
            sms_to_groom_phone=user_in.sms_to_groom_phone,
            otp_expiration=datetime.utcnow() + timedelta(hours=2),
            created_at=datetime.utcnow(),
            status=UserStatus.active,
        )

        logger.info(f"🔵 Adding user to database...")
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"✅ User created successfully with ID: {user.id}")

        # Send OTP
        try:
            logger.info(
                f"🔵 Sending OTP to {'groom' if user_in.sms_to_groom_phone else 'guardian'}...")
            if user_in.sms_to_groom_phone == True:
                send_otp_to_user_by_twilo(user.phone_number, otp_code)
            else:
                send_otp_to_user_by_twilo(user.guardian_phone, otp_code)
            logger.info(f"✅ OTP sent successfully")
        except ValueError as e:
            logger.error(f"❌ SMS failed: {str(e)}")
            db.delete(user)
            db.commit()
            return {
                "message": " فشل إرسال الرمز",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"❌ Unexpected SMS error: {str(e)}")
            logger.error(traceback.format_exc())
            db.delete(user)
            db.commit()
            raise HTTPException(
                status_code=500, detail=f"خطأ في إرسال الرمز: {str(e)}")

        logger.info(f"🔵 Preparing response...")

        # Explicitly create UserOut to check for validation issues
        try:
            user_out = UserOut(
                id=user.id,
                phone_number=user.phone_number,
                role=user.role,
                phone_verified=user.phone_verified,
                created_at=user.created_at,
                status=user.status,
                first_name=user.first_name,
                last_name=user.last_name,
                father_name=user.father_name,
                grandfather_name=user.grandfather_name,
                birth_date=user.birth_date,
                birth_address=user.birth_address,
                home_address=user.home_address,
                clan_id=user.clan_id,
                county_id=user.county_id,
                guardian_name=user.guardian_name,
                guardian_phone=user.guardian_phone,
                guardian_home_address=user.guardian_home_address,
                guardian_birth_address=user.guardian_birth_address,
                guardian_birth_date=user.guardian_birth_date,
                guardian_relation=user.guardian_relation,
                access_pages_password_hash=user.access_pages_password_hash
            )
            logger.info(f"✅ UserOut created successfully")
        except Exception as e:
            logger.error(f"❌ UserOut validation failed: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500, detail=f"خطأ في إنشاء بيانات المستخدم: {str(e)}")

        response = {
            "message": "تم إنشاء الحساب. تحقق من هاتفك",
            "user": user_out
        }
        logger.info(f"✅ Registration completed successfully")
        return response

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in register_groom: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"حدث خطأ غير متوقع: {str(e)}"
        )


@router.post("/verify-phone")
def verify_phone(phone_number: str = Body(...), code: str = Body(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.phone_number == phone_number).first()

    if not user:
        user_by_guardian_phone = db.query(User).filter(
            User.guardian_phone == phone_number).first()
        if not user_by_guardian_phone:
            raise HTTPException(status_code=404, detail="المستخدم غير موجود")

        user = user_by_guardian_phone

    if user.phone_verified:
        # return {"message": "الهاتف مؤكد بالفعل."}
        raise HTTPException(status_code=404, detail="الهاتف مؤكد بالفعل")

    if user.otp_code != code:
        raise HTTPException(
            status_code=400, detail=f"رمز التحقق غير صحيح ")

    if user.otp_expiration < datetime.utcnow():
        raise HTTPException(
            status_code=400, detail="انتهت صلاحية رمز التحقق")

    user.phone_verified = True
    user.otp_code = None
    user.otp_expiration = None
    db.commit()

    return {"message": "تم تأكيد رقم الهاتف. يمكنك الآن تسجيل الدخول."}


class PhoneRequest(BaseModel):
    phone_number: str


@router.post("/resend-verification")
def resend_otp(payload: PhoneRequest, db: Session = Depends(get_db)):
    phone_number = payload.phone_number

    user = db.query(User).filter(User.phone_number == phone_number).first()

    if not user:
        user_by_guardian_phone = db.query(User).filter(
            User.guardian_phone == phone_number).first()
        if not user_by_guardian_phone:
            raise HTTPException(status_code=404, detail="المستخدم غير موجود")

        user = user_by_guardian_phone

    # if user.phone_verified:
    #     return {"message": "الهاتف مؤكد بالفعل."}

    user.phone_verified = False
    new_code = generate_otp_code()
    user.otp_code = new_code
    user.otp_expiration = datetime.utcnow() + timedelta(hours=2)
    db.commit()

    # Send new OTP
    try:
        send_otp_to_user_by_twilo(phone_number, new_code)
        return {"message": "تم إرسال رمز تحقق جديد إلى هاتفك."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resend-verification/dev_mode")
def resend_otp(payload: PhoneRequest, db: Session = Depends(get_db)):
    phone_number = payload.phone_number

    user = db.query(User).filter(User.phone_number == phone_number).first()

    if not user:
        user_by_guardian_phone = db.query(User).filter(
            User.guardian_phone == phone_number).first()
        if not user_by_guardian_phone:
            raise HTTPException(status_code=404, detail="المستخدم غير موجود")

        user = user_by_guardian_phone

    print(
        f"Debug: User found - ID: {user.id}, Phone: {user.phone_number}, Guardian Phone: {user.guardian_phone}")
    # if user.phone_verified:
    #     return {"message": "الهاتف مؤكد بالفعل."}

    user.phone_verified = False
    new_code = generate_otp_code()
    user.otp_code = new_code
    user.otp_expiration = datetime.utcnow() + timedelta(hours=2)
    db.commit()

    return {"message": "تم إرسال رمز تحقق جديد إلى هاتفك.", "otp_code": new_code,  "phone_number": phone_number,  "guardian_phone": user.guardian_phone}

    # # Send new OTP
    # try:
    #     send_otp_to_user_by_twilo(phone_number, new_code)
    #     return {"message": "تم إرسال رمز تحقق جديد إلى هاتفك."}
    # except ValueError as e:
    #     raise HTTPException(status_code=400, detail=str(e))


# for updating nuber case
@router.post("/verify-new-phone")
def verify_new_phone(
    code: str = Body(...),
    db: Session = Depends(get_db),
    current: User = Depends(groom_required)
):
    if not current.temp_phone_number:
        raise HTTPException(
            status_code=400, detail="لا يوجد تحديث رقم هاتف معلق.")

    if current.temp_phone_otp_code != code:
        raise HTTPException(
            status_code=400, detail="رمز التحقق غير صحيح.")

    if current.temp_phone_otp_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=400, detail="انتهت صلاحية رمز التحقق.")

    # ✅ On success — apply new phone number and cleanup
    current.phone_number = current.temp_phone_number
    current.phone_verified = True

    current.temp_phone_number = None
    current.temp_phone_otp_code = None
    current.temp_phone_otp_expires_at = None

    db.commit()

    return {"message": "تم تحديث رقم الهاتف وتأكيده بنجاح."}


# get users OTP code for super admin
@router.get("/get_otp/{phone_number}", dependencies=[Depends(super_admin_required)])
def get_otp_code(phone_number: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == phone_number).first()

    if not user:
        user_by_guardian_phone = db.query(User).filter(
            User.guardian_phone == phone_number).first()
        if not user_by_guardian_phone:
            raise HTTPException(status_code=404, detail="المستخدم غير موجود")

        user = user_by_guardian_phone

    if not user.otp_code:
        raise HTTPException(
            status_code=404, detail="لا يوجد رمز تحقق لهذا المستخدم")

    return {"otp_code": user.otp_code}

# get users OTP code for Clan admin


@router.get("/clan_admin/get_otp/{phone_number}", dependencies=[Depends(clan_admin_required)])
def get_otp_code(phone_number: str, db: Session = Depends(get_db), current: User = Depends(clan_admin_required)):
    user = db.query(User).filter(
        User.clan_id == current.clan_id,
        User.phone_number == phone_number,
    ).first()

    if not user:
        user_by_guardian_phone = db.query(User).filter(
            User.clan_id == current.clan_id,
            User.guardian_phone == phone_number).first()
        if not user_by_guardian_phone:
            raise HTTPException(status_code=404, detail="المستخدم غير موجود")

        user = user_by_guardian_phone

    if not user.otp_code:
        raise HTTPException(
            status_code=404, detail="لا يوجد رمز تحقق لهذا المستخدم")

    return {"otp_code": user.otp_code}


@router.post("/request-password-reset")
def request_password_reset(
    payload: PhoneRequest,
    db: Session = Depends(get_db)
):
    phone_number = payload.phone_number

    user = db.query(User).filter(User.phone_number == phone_number).first()

    if not user:
        user_by_guardian_phone = db.query(User).filter(
            User.guardian_phone == phone_number).first()
        if not user_by_guardian_phone:
            raise HTTPException(status_code=404, detail="المستخدم غير موجود")

        user = user_by_guardian_phone

    # if not user.phone_verified:
    #     raise HTTPException(
    #         status_code=400,
    #         detail="رقم الهاتف غير مؤكد"
    #     )

    # Generate new OTP for password reset
    new_code = generate_otp_code()
    user.otp_code = new_code
    user.otp_expiration = datetime.utcnow() + timedelta(hours=2)
    db.commit()

    # Send new OTP
    try:
        send_otp_to_user_by_twilo(phone_number, new_code)
        return {"message": "تم إرسال رمز التحقق لإعادة تعيين كلمة المرور إلى هاتفك."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ResetPasswordRequest(BaseModel):
    phone_number: str
    otp_code: str
    new_password: str


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.phone_number == request.phone_number
    ).first()

    if not user:
        user_by_guardian_phone = db.query(User).filter(
            User.guardian_phone == request.phone_number).first()
        if not user_by_guardian_phone:
            raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    user = user_by_guardian_phone

    if not user.phone_verified:
        raise HTTPException(
            status_code=400,
            detail="رقم الهاتف غير مؤكد"
        )

    if user.otp_expiration is not None:
        if user.otp_code != request.otp_code:
            raise HTTPException(
                status_code=400,
                detail="رمز التحقق غير صحيح"
            )

    if user.otp_expiration is not None:
        if user.otp_expiration < datetime.utcnow():
            raise HTTPException(
                status_code=400,
                detail="انتهت صلاحية رمز التحقق"
            )

    # Update password and clear OTP
    user.password_hash = auth_utils.get_password_hash(request.new_password)
    user.otp_code = None
    user.otp_expiration = None
    db.commit()

    return {"message": "تم تغيير كلمة المرور بنجاح. يمكنك الآن تسجيل الدخول."}


@router.put("/update-groom/{groom_id}", response_model=UserOut)
def update_groom_info(
    groom_id: int,
    update_data: UpdateGroomRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(clan_admin_required)
):
    """Update groom information by clan admin"""

    # Find the groom
    groom = db.query(User).filter(
        User.id == groom_id,
        User.role == UserRole.groom
    ).first()

    if not groom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="العريس غير موجود"
        )

    # Check if groom belongs to admin's clan
    if groom.clan_id != current_admin.clan_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="لا يمكنك تعديل معلومات عريس من عشيرة أخرى"
        )

    # Update fields that are not None
    update_fields = [
        'first_name', 'last_name', 'father_name', 'grandfather_name',
        'birth_date', 'birth_address', 'home_address', 'phone_number',
        'guardian_name', 'guardian_phone', 'guardian_home_address',
        'guardian_birth_address', 'guardian_birth_date', 'guardian_relation', 'status'
    ]

    for field in update_fields:
        value = getattr(update_data, field)
        if value is not None:
            setattr(groom, field, value)

    db.commit()
    db.refresh(groom)

    return groom


# ---------------------------------------------------------
# side of password access pages


@router.post("/verify-access-password")
def verify_user_access_password(
    verify_data: AccessPasswordVerify,
    db: Session = Depends(get_db),
    current: User = Depends(auth_utils.get_current_user)
):
    """
    Verify access password for special pages.
    Works for clan admins and grooms.
    """
    # Super admins don't need access passwords
    if current.role == UserRole.super_admin:
        return {
            "valid": True,
            "message": "المسؤول الأعلى لديه وصول كامل"
        }

    # Check if user has access password set
    if not current.access_pages_password_hash:
        raise HTTPException(
            status_code=403,
            detail="لم يتم تعيين كلمة مرور الوصول لهذا المستخدم"
        )

    # Verify password
    is_valid = verify_access_password(
        verify_data.access_password,
        current.access_pages_password_hash
    )

    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="كلمة مرور الوصول غير صحيحة"
        )

    return {
        "valid": True,
        "message": "تم التحقق من كلمة مرور الوصول بنجاح"
    }
