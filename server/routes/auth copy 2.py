# from fastapi import APIRouter, Body, Depends, HTTPException, status
# from platformdirs import user_config_dir
# from pydantic import BaseModel
# from sqlalchemy.orm import Session
# from datetime import datetime, timedelta

# from server.models.user import User, UserRole, UserStatus
# from server.models.clan import Clan
# from server.models.county import County
# from server.schemas.user import UserCreate, UserOut
# from server.schemas.auth import LoginRequest, RegisterResponse, Token
# from server.utils.otp_utils import send_otp_to_user, generate_otp_code
# from server.routes.grooms import groom_required
# from server.utils.phone_utils import validate_algerian_number, validate_number_phone, validate_number_phone_of_guardian
# from .. import auth_utils
# from ..db import get_db

# router = APIRouter(prefix="/auth", tags=["auth"])


# # get role of the user
# @router.get("/get_role", response_model=UserOut)
# def get_user_role(
#     db: Session = Depends(get_db),
#     current: User = Depends(auth_utils.get_current_user)
# ):
#     user_info = db.query(User).filter(User.id == current.id).first()
#     if not user_info:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )

#     return user_info


# @router.delete("/delet_user/{phone__number}")
# def delet_user(phone__number: int, db: Session = Depends(get_db)):
#     user = db.query(User).filter(
#         User.phone_number == phone__number
#     ).first()

#     return {'message': f'user with this phone number{phone__number} deletd secssefely'}


# @router.get("/me", response_model=UserOut)
# def get_current_user_info(
#     db: Session = Depends(get_db),
#     current: User = Depends(auth_utils.get_current_user)
# ):
#     user_info = db.query(User).filter(User.id == current.id).first()
#     if not user_info:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )

#     return user_info


# # @router.post("/login", response_model=Token)
# # def login(
# #     request: LoginRequest,
# #     db: Session = Depends(get_db),
# # ):
# #     user = auth_utils.authenticate_user(
# #         db, request.phone_number, request.password
# #     )

# #     if not user:
# #         raise HTTPException(
# #             status_code=status.HTTP_401_UNAUTHORIZED,
# #             detail="Invalid phone number or password"
# #         )

# #     if not user.phone_verified:
# #         raise HTTPException(
# #             status_code=status.HTTP_403_FORBIDDEN,
# #             detail="Phone number not verified"
# #         )

# #     access_token = auth_utils.create_access_token(
# #         data={"sub": str(user.id), "role": user.role}
# #     )

# #     return {
# #         "access_token": access_token,
# #         "token_type": "bearer"
# #     }

# @router.post("/login", response_model=Token)
# def login(
#     request: LoginRequest,
#     db: Session = Depends(get_db),
# ):
#     user = auth_utils.authenticate_user(
#         db, request.phone_number, request.password
#     )

#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid phone number or password"
#         )

#     if not user.phone_verified:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Phone number not verified"
#         )

#     # Check if user status is active
#     if user.status != UserStatus.active:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Your account is not active. Please check with your clan admin for assistance."
#         )

#     access_token = auth_utils.create_access_token(
#         data={"sub": str(user.id), "role": user.role}
#     )

#     return {
#         "access_token": access_token,
#         "token_type": "bearer"
#     }

# @router.post("/register/groom", response_model=RegisterResponse)
# def register_groom(user_in: UserCreate, db: Session = Depends(get_db)):
#     if user_in.role != UserRole.groom:
#         raise HTTPException(
#             status_code=400, detail="Only grooms can self-register")

#  # Check for existing user with this phone number
#     existing_user = db.query(User).filter(
#         User.phone_number == user_in.phone_number).first()

#     if existing_user:
#         if existing_user.phone_verified:
#             # Phone is verified, don't allow registration
#             raise HTTPException(
#                 status_code=400, detail="Phone number already exists and is verified")
#         else:
#             # Phone is not verified, delete the old unverified user
#             db.delete(existing_user)
#             db.commit()

#     clan = db.query(Clan).filter(Clan.id == user_in.clan_id).first()
#     if not clan:
#         raise HTTPException(
#             status_code=404, detail=f"Clan ID {user_in.clan_id} not found.")

#     county = db.query(County).filter(County.id == user_in.county_id).first()
#     if not county:
#         raise HTTPException(
#             status_code=404, detail=f"County ID {user_in.county_id} not found.")

#     if clan.county_id != county.id:
#         raise HTTPException(
#             status_code=404, detail="Clan does not belong to this county.")

#     hashed_password = auth_utils.get_password_hash(user_in.password)
#     otp_code = generate_otp_code()
#     # guardian_phone = validate_algerian_number(user_in.guardian_phone)
#     validate_number_phone(user_in.phone_number)
#     validate_number_phone_of_guardian(user_in.guardian_phone)
#     user = User(
#         phone_number=user_in.phone_number,
#         password_hash=hashed_password,
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
#         otp_expiration=datetime.utcnow() + timedelta(hours=2),
#         # New fields from updated model
#         created_at=datetime.utcnow(),
#         status=UserStatus.active,
#     )

#     db.add(user)
#     db.commit()
#     db.refresh(user)

#     # send_otp_to_user(user.phone_number, otp_code)

#     return {
#         "message": "Account created. Check your phone for verification code.",
#         "user": user
#     }


# @router.post("/verify-phone")
# def verify_phone(phone_number: str = Body(...), code: str = Body(...), db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.phone_number == phone_number).first()

#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     if user.phone_verified:
#         return {"message": "Phone already verified."}

#     if user.otp_code != code:
#         raise HTTPException(
#             status_code=400, detail="Invalid verification code")

#     if user.otp_expiration < datetime.utcnow():
#         raise HTTPException(
#             status_code=400, detail="Verification code expired")

#     user.phone_verified = True
#     user.otp_code = None
#     user.otp_expiration = None
#     db.commit()

#     return {"message": "Phone number verified. You can now log in."}


# class PhoneRequest(BaseModel):
#     phone_number: str


# @router.post("/resend-verification")
# def resend_otp(payload: PhoneRequest, db: Session = Depends(get_db)):
#     phone_number = payload.phone_number

#     user = db.query(User).filter(User.phone_number == phone_number).first()

#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     if user.phone_verified:
#         return {"message": "Phone already verified."}

#     new_code = generate_otp_code()
#     user.otp_code = new_code
#     user.otp_expiration = datetime.utcnow() + timedelta(hours=2)
#     db.commit()

#     # send_otp_to_user(user.phone_number, new_code)

#     return {"message": "A new verification code has been sent to your phone."}


# # for updating nuber case
# @router.post("/verify-new-phone")
# def verify_new_phone(
#     code: str = Body(...),
#     db: Session = Depends(get_db),
#     current: User = Depends(groom_required)
# ):
#     if not current.temp_phone_number:
#         raise HTTPException(
#             status_code=400, detail="No phone number update pending.")

#     if current.temp_phone_otp_code != code:
#         raise HTTPException(
#             status_code=400, detail="Invalid verification code.")

#     if current.temp_phone_otp_expires_at < datetime.utcnow():
#         raise HTTPException(
#             status_code=400, detail="Verification code expired.")

#     # ✅ On success — apply new phone number and cleanup
#     current.phone_number = current.temp_phone_number
#     current.phone_verified = True

#     current.temp_phone_number = None
#     current.temp_phone_otp_code = None
#     current.temp_phone_otp_expires_at = None

#     db.commit()

#     return {"message": "Phone number updated and verified successfully."}
