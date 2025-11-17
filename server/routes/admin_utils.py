from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db import get_db
from ..models.user import User, UserRole
from ..auth_utils import get_password_hash, get_current_user

router = APIRouter(prefix="/admin_util", tags=["Admin Utils"])


class PasswordResetRequest(BaseModel):
    phone_number: str
    new_password: str


@router.post("/reset-super_ad_ps")
async def reset_superadmin_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reset super admin password - Only accessible by super admins
    """
    # Verify current user is super admin
    if current_user.role == UserRole.groom:
        raise HTTPException(status_code=403, detail="Only super ad")

    # Find the user
    user = db.query(User).filter(User.phone_number ==
                                 request.phone_number).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=403, detail="Can only reset super admin passwords")

    # Update password
    user.password_hash = get_password_hash(request.new_password)
    db.commit()

    return {
        "message": "Super admin password reset successfully",
        "phone_number": request.phone_number
    }
