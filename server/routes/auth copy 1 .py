# """
# Authentication routes: login, register (groom).
# """
# from datetime import datetime, timedelta
# import random
# from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
# from sqlalchemy.orm import Session

# from server.models.clan import Clan
# from server.models.county import County
# from server.utils.phone_utils import validate_algerian_number
# from server.utils.sms import send_otp_sms
# from .. import auth_utils
# from ..db import get_db
# from ..models.user import User, UserRole
# from ..schemas.auth import LoginRequest, Token
# from ..schemas.user import UserBase, UserCreate, UserOut

# router = APIRouter(
#     prefix="/auth",
#     tags=["auth"]
# )


# @router.post("/login", response_model=Token)
# def login(request: LoginRequest, db: Session = Depends(get_db), current: User = Depends(auth_utils.phone_verified_required)):
#     user = auth_utils.authenticate_user(
#         db, request.phone_number, request.password)
#     if not user:
#         raise HTTPException(
#             status_code=400, detail="Invalid phone number or password")
#     if not user.phone_verified:
#         raise HTTPException(
#             status_code=403, detail="Phone number not verified")

#     access_token = auth_utils.create_access_token(
#         data={"sub": str(user.id), "role": user.role}
#         # data={"sub": user.id, "role": user.role}
#     )
#     return {"access_token": access_token, "token_type": "bearer"}


# @router.post("/register/groom", response_model=UserOut)
# def register_groom(user_in: UserCreate, db: Session = Depends(get_db)):
#     # Only allow grooms to register through this endpoint

#     if user_in.role != UserRole.groom:
#         raise HTTPException(
#             status_code=400, detail="Only grooms can self-register")
#     existing = db.query(User).filter(
#         User.phone_number == user_in.phone_number).first()
#     if existing:
#         raise HTTPException(
#             status_code=400, detail="Phone number already exist")

#     # checking clan existing
#     check_clan = db.query(Clan).filter(
#         Clan.id == user_in.clan_id
#     ).first()
#     if not check_clan:
#         raise HTTPException(
#             status_code=404, detail=f"clan with this id {user_in.clan_id} not found.")

#     # checking county existing
#     check_county = db.query(County).filter(
#         County.id == user_in.county_id
#     ).first()
#     if not check_county:
#         raise HTTPException(
#             status_code=404, detail=f"county with this id {user_in.county_id} not found.")

#     check_exist_clan_on_county = db.query(Clan).filter(
#         Clan.id == user_in.clan_id,
#         Clan.county_id == user_in.county_id
#     ).first()
#     if not check_exist_clan_on_county:
#         raise HTTPException(
#             status_code=404, detail=f"this clan id {user_in.clan_id} not found on this county id {user_in.county_id} .")
#     hashed = auth_utils.get_password_hash(user_in.password)
#     user = User(
#         phone_number=user_in.phone_number,
#         password_hash=hashed,
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
#         guardian_relation=user_in.guardian_relation,
#     )
#     db.add(user)
#     db.commit()
#     db.refresh(user)


#     return {"message": "Account created. Check your phone for verification code.",
#             "user": user}
#     # return user


# @router.get("/me", response_model=UserOut)
# def get_me(current_user: User = Depends(auth_utils.get_current_user)):
#     """
#     Get current logged-in user profile.
#     """
#     return current_user


# def generate_otp():
#     return str(random.randint(100000, 999999))


# @router.post("/send-otp")
# def send_otp(phone_number: str = Query(...), db: Session = Depends(get_db)):
#     formatted_number = validate_algerian_number(phone_number)

#     user = db.query(User).filter(User.phone_number == formatted_number).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     otp = generate_otp()
#     user.otp_code = otp
#     user.otp_expiration = datetime.utcnow() + timedelta(minutes=10)
#     db.commit()

#     try:
#         send_otp_sms(formatted_number, otp)
#     except Exception as e:
#         raise HTTPException(
#             status_code=500, detail="Failed to send OTP via SMS")

#     return {"message": "OTP sent successfully via SMS"}


# @router.post("/verify-otp")
# def verify_otp(phone_number: str = Query(...), otp_code: str = Query(...), db: Session = Depends(get_db)):
#     formatted_number = validate_algerian_number(phone_number)

#     user = db.query(User).filter(User.phone_number == formatted_number).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     if user.otp_code != otp_code:
#         raise HTTPException(status_code=400, detail="Invalid OTP code")

#     if user.otp_expiration < datetime.utcnow():
#         raise HTTPException(status_code=400, detail="OTP has expired")

#     user.phone_verified = True
#     user.otp_code = None
#     user.otp_expiration = None
#     db.commit()

#     return {"message": "Phone number verified successfully"}

