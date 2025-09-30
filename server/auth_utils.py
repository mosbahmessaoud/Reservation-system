"""
Authentication utilities: JWT handling, password hashing, security dependencies.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .db import SessionLocal
from .models.user import User

from passlib.context import CryptContext
import hashlib
# ✅ Load environment variables
load_dotenv()

# ✅ Get SECRET_KEY from environment (CRITICAL for production!)
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey2")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))  # 24 hours default

# ✅ Warn if using default secret key
if SECRET_KEY == "supersecretkey2":
    print("⚠️ WARNING: Using default SECRET_KEY! Please set SECRET_KEY in environment variables!")

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Good security level
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hashed password.
    Handles the pre-hashing for long passwords.
    """
    try:
        password_bytes = plain_password.encode('utf-8')

        # Apply same pre-hashing logic as hash_password
        if len(password_bytes) > 72:
            password_hash = hashlib.sha256(password_bytes).hexdigest()
            return pwd_context.verify(password_hash, hashed_password)

        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # Log the error for debugging
        print(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt with proper length handling.
    Bcrypt has a 72-byte limit, so we pre-hash with SHA256 for long passwords.
    """
    # Pre-hash the password with SHA256 to ensure it's always within bcrypt's 72-byte limit
    # This is a recommended approach for handling bcrypt's limitation
    password_bytes = password.encode('utf-8')

    # Use SHA256 to create a fixed-length hash before bcrypt
    if len(password_bytes) > 72:
        # For passwords longer than 72 bytes, pre-hash with SHA256
        password_hash = hashlib.sha256(password_bytes).hexdigest()
        return pwd_context.hash(password_hash)

    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token

    Args:
        data: Dictionary containing user data (must include 'sub' for user_id)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token as string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})

    # ✅ Add issued at timestamp
    to_encode.update({"iat": datetime.utcnow()})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_user_by_phone(db: Session, phone_number: str) -> Optional[User]:
    """Get user by phone number"""
    return db.query(User).filter(User.phone_number == phone_number).first()


def authenticate_user(db: Session, phone_number: str, password: str) -> Optional[User]:
    """
    Authenticate user with phone number and password

    Args:
        db: Database session
        phone_number: User's phone number
        password: Plain text password

    Returns:
        User object if authentication succeeds, None otherwise
    """
    user = get_user_by_phone(db, phone_number)

    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Get current user from JWT token

    Args:
        db: Database session
        token: JWT token from Authorization header

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    # ✅ Only log in development
    is_production = os.getenv("ENVIRONMENT") == "production"

    if not is_production:
        print(f"🔐 Received token: {token[:20]}...")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if not is_production:
            print(f"✅ Decoded payload: {payload}")

        # Extract user_id from 'sub' claim
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user ID (sub)",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract role from token
        role = payload.get("role")
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user role",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Convert user_id to integer
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID in token is invalid",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except JWTError as e:
        if not is_production:
            print(f"❌ JWT Error: {e}")
        raise credentials_exception

    # Query user from database
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(*required_roles):
    """
    Dependency factory for role-based access control

    Args:
        *required_roles: Variable number of allowed UserRole values

    Returns:
        Dependency function that checks user role

    Example:
        @app.get("/admin")
        async def admin_route(user = Depends(require_role(UserRole.admin, UserRole.super_admin))):
            ...
    """
    def _require_role(current_user: User = Depends(get_current_user)) -> User:
        # Check if user has required role
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in required_roles]}"
            )

        # Check if phone is verified
        if not current_user.phone_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Phone number not verified. Please verify your phone to access this resource."
            )

        return current_user

    return _require_role


def phone_verified_required(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to check if user's phone is verified

    Args:
        current_user: Current authenticated user

    Returns:
        User object if phone is verified

    Raises:
        HTTPException: If phone is not verified
    """
    if not current_user.phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone number not verified. Please verify your phone number first."
        )
    return current_user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get current active user (not banned/disabled)

    Args:
        current_user: Current authenticated user

    Returns:
        User object if active

    Raises:
        HTTPException: If user is inactive
    """
    # Add this field to your User model if needed
    if hasattr(current_user, 'is_active') and not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user


# ✅ Optional: Token refresh utility
def create_refresh_token(data: dict) -> str:
    """
    Create refresh token with longer expiration

    Args:
        data: Dictionary containing user data

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    # Refresh tokens expire in 7 days
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_refresh_token(token: str) -> Optional[dict]:
    """
    Verify and decode refresh token

    Args:
        token: JWT refresh token

    Returns:
        Decoded payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            return None

        return payload
    except JWTError:
        return None
