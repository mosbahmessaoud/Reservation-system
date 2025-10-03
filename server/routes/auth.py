
#server\routes\auth.py
from fastapi import APIRouter, Body, Depends, HTTPException, status
from platformdirs import user_config_dir
from pydantic import BaseModel
import sqlalchemy
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from server.models.user import User, UserRole, UserStatus
from server.models.clan import Clan
from server.models.county import County
from server.schemas.user import UpdateGroomRequest, UserCreate, UserOut
from server.schemas.auth import LoginRequest, RegisterResponse, Token
from server.utils.otp_utils import send_otp_to_user_by_twilo, generate_otp_code
from server.routes.grooms import groom_required
from server.utils.phone_utils import validate_algerian_number, validate_number_phone, validate_number_phone_of_guardian
from server.routes.clan_admin import clan_admin_required
from .. import auth_utils
from ..db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


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
def delet_user(phone__number: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.phone_number == phone__number
    ).first()

    return {'message': f'تم حذف المستخدم صاحب رقم الهاتف {phone__number} بنجاح'}


@router.get("/me", response_model=UserOut)
def get_current_user_info(
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


@router.post("/login", response_model=Token)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):

    print(f"🔍 Login attempt for: {request.phone_number}")
    print(f"🔍 Password length: {len(request.password)} chars")
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

    access_token = auth_utils.create_access_token(
        data={"sub": str(user.id), "role": user.role}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/register/groom", response_model=RegisterResponse)
def register_groom(user_in: UserCreate, db: Session = Depends(get_db)):
    if user_in.role != UserRole.groom:
        raise HTTPException(
            status_code=400, detail="يمكن للعرسان فقط التسجيل بأنفسهم")

 # Check for existing user with this phone number
    existing_user = db.query(User).filter(
        User.phone_number == user_in.phone_number).first()

    if existing_user:
        if existing_user.phone_verified:
            # Phone is verified, don't allow registration
            raise HTTPException(
                status_code=400, detail="رقم الهاتف موجود بالفعل ومؤكد")
        else:
            # Phone is not verified, delete the old unverified user
            db.delete(existing_user)
            db.commit()

    clan = db.query(Clan).filter(Clan.id == user_in.clan_id).first()
    if not clan:
        raise HTTPException(
            status_code=404, detail=f"معرف العشيرة {user_in.clan_id} غير موجود.")

    county = db.query(County).filter(County.id == user_in.county_id).first()
    if not county:
        raise HTTPException(
            status_code=404, detail=f"معرف المقاطعة {user_in.county_id} غير موجود.")

    if clan.county_id != county.id:
        raise HTTPException(
            status_code=404, detail="العشيرة لا تنتمي إلى هذه المقاطعة.")

    hashed_password = auth_utils.get_password_hash(user_in.password)
    otp_code = generate_otp_code()
    # guardian_phone = validate_algerian_number(user_in.guardian_phone)
    validate_number_phone(user_in.phone_number)
    validate_number_phone_of_guardian(user_in.guardian_phone)
    user = User(
        phone_number=user_in.phone_number,
        password_hash=hashed_password,
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
        otp_expiration=datetime.utcnow() + timedelta(hours=2),
        # New fields from updated model
        created_at=datetime.utcnow(),
        status=UserStatus.active,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # send_otp_to_user_by_twilo(user.phone_number, otp_code)

    return {
        "message": "تم إنشاء الحساب. تحقق من هاتفك للحصول على رمز التحقق.",
        "user": user
    }


@router.post("/verify-phone")
def verify_phone(phone_number: str = Body(...), code: str = Body(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == phone_number).first()

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    if user.phone_verified:
        # return {"message": "الهاتف مؤكد بالفعل."}
        raise HTTPException(status_code=404, detail="الهاتف مؤكد بالفعل")

    if user.otp_code != code:
        raise HTTPException(
            status_code=400, detail="رمز التحقق غير صحيح")

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
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    # if user.phone_verified:
    #     return {"message": "الهاتف مؤكد بالفعل."}

    user.phone_verified = False
    new_code = generate_otp_code()
    user.otp_code = new_code
    user.otp_expiration = datetime.utcnow() + timedelta(hours=2)
    db.commit()

    # send_otp_to_user_by_twilo(user.phone_number, new_code)

    return {"message": "تم إرسال رمز تحقق جديد إلى هاتفك."}


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


# get users OTP code for admins
@router.get("/get_otp/{phone_number}")
def get_otp_code(phone_number: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == phone_number).first()

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

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
        raise HTTPException(
            status_code=404,
            detail="المستخدم غير موجود"
        )

    if not user.phone_verified:
        raise HTTPException(
            status_code=400,
            detail="رقم الهاتف غير مؤكد"
        )

    # Generate new OTP for password reset
    new_code = generate_otp_code()
    user.otp_code = new_code
    user.otp_expiration = datetime.utcnow() + timedelta(hours=2)
    db.commit()

    # send_otp_to_user_by_twilo(user.phone_number, new_code)

    return {"message": "تم إرسال رمز التحقق لإعادة تعيين كلمة المرور إلى هاتفك."}


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
        raise HTTPException(
            status_code=404,
            detail="المستخدم غير موجود"
        )

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
