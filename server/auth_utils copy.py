# """
# Authentication utilities: JWT handling, password hashing, security dependencies.
# """
# from datetime import datetime, timedelta
# from typing import Optional
# from jose import jwt, JWTError
# from passlib.context import CryptContext
# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from sqlalchemy.orm import Session

# from .db import SessionLocal
# from .models.user import User
# from .schemas.auth import TokenData

# # Secret key for JWT (change this in production)
# SECRET_KEY = "supersecretkey2"
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# def verify_password(plain_password, hashed_password):
#     return pwd_context.verify(plain_password, hashed_password)


# def get_password_hash(password):
#     return pwd_context.hash(password)


# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# def get_user_by_phone(db: Session, phone_number: str):
#     return db.query(User).filter(User.phone_number == phone_number).first()


# def authenticate_user(db: Session, phone_number: str, password: str):
#     user = get_user_by_phone(db, phone_number)

#     if not user or not verify_password(password, user.password_hash):
#         return None
#     return user


# def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
#     print(f"---------------------++++++  Received token: {token}")
#     print(f"SECRET_KEY: {SECRET_KEY}")
#     print(f"ALGORITHM: {ALGORITHM}")
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         print(f"Decoded payload: {payload}")
#     except JWTError as e:
#         print(f"JWTError: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid or expired token",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     # user_id = payload.get("sub")
#     user_id = payload.get("sub")
#     user_id = int(user_id)
#     if user_id is None:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token missing user ID (sub).",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     role = payload.get("role")
#     if role is None:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token missing user role.",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     # Ensure user_id is int for DB lookup
#     try:
#         user_id = int(user_id)
#     except (ValueError, TypeError):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="User ID in token is invalid.",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     user = db.query(User).filter(User.id == user_id).first()
#     if user is None:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="User not found.",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     return user


# def require_role(required_roles):
#     # Dependency factory for role-based access
#     def _require_role(current_user: User = Depends(get_current_user)):

#         if current_user.role not in required_roles:
#             raise HTTPException(
#                 status_code=403, detail="Insufficient permissions")
#         if not current_user.phone_verified:
#             raise HTTPException(
#                 status_code=403, detail="Phone number not verified")
#         return current_user
#     return _require_role


# def phone_verified_required(current_user: User = Depends(get_current_user)):
#     if not current_user.phone_verified:
#         raise HTTPException(
#             status_code=403, detail="Phone number not verified")
#     return current_user
