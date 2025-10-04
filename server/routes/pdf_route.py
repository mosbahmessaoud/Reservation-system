"""
Simplified PDF generation and download routes.
"""
import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from server.utils.pdf_generator import generate_wedding_pdf
from server.models.reservation import Reservation
from server.models.user import User, UserRole
from ..auth_utils import get_current_user, get_db

router = APIRouter(prefix="/pdf", tags=["pdf"])
logger = logging.getLogger(__name__)


@router.post("/generate/{reservation_id}")
def generate_pdf(
    reservation_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """Generate PDF for a reservation."""
    # Get reservation
    reservation = db.query(Reservation).filter(
        Reservation.id == reservation_id,
        Reservation.groom_id == current.id
    ).first()

    if not reservation:
        raise HTTPException(404, "الحجز غير موجود")

    # Check if PDF already exists
    if reservation.pdf_url and os.path.exists(reservation.pdf_url):
        return {
            "message": "PDF موجود بالفعل",
            "pdf_url": f"/pdf/download/{reservation.id}"
        }

    # Generate PDF
    try:
        pdf_path = generate_wedding_pdf(reservation, "generated_pdfs", db)
        reservation.pdf_url = pdf_path
        db.commit()

        return {
            "message": "تم إنشاء PDF بنجاح",
            "pdf_url": f"/pdf/download/{reservation.id}"
        }
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(500, f"خطأ في إنشاء PDF: {str(e)}")


@router.post("/regenerate/{reservation_id}")
def regenerate_pdf(
    reservation_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """Force regenerate PDF (overwrites existing)."""
    reservation = db.query(Reservation).filter(
        Reservation.id == reservation_id,
        Reservation.groom_id == current.id
    ).first()

    if not reservation:
        raise HTTPException(404, "الحجز غير موجود")

    try:
        pdf_path = generate_wedding_pdf(reservation, "generated_pdfs", db)
        reservation.pdf_url = pdf_path
        db.commit()

        return {
            "message": "تم إعادة إنشاء PDF بنجاح",
            "pdf_url": f"/pdf/download/{reservation.id}"
        }
    except Exception as e:
        logger.error(f"PDF regeneration failed: {e}")
        raise HTTPException(500, f"خطأ في إعادة إنشاء PDF: {str(e)}")


@router.get("/download/{reservation_id}")
def download_pdf(
    reservation_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """Download PDF for a reservation."""
    reservation = db.query(Reservation).filter(
        Reservation.id == reservation_id
    ).first()

    if not reservation:
        raise HTTPException(404, "الحجز غير موجود")

    # Check permissions: groom or clan admin
    is_groom = current.id == reservation.groom_id
    is_clan_admin = (
        current.role == UserRole.clan_admin and
        current.clan_id == reservation.clan_id
    )

    if not (is_groom or is_clan_admin):
        raise HTTPException(403, "غير مصرح لك بتحميل هذا الملف")

    # Check if PDF exists
    if not reservation.pdf_url or not os.path.exists(reservation.pdf_url):
        raise HTTPException(404, "ملف PDF غير موجود")

    return FileResponse(
        reservation.pdf_url,
        media_type="application/pdf",
        filename=f"reservation_{reservation_id}.pdf"
    )


@router.get("/status/{reservation_id}")
def check_pdf_status(
    reservation_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """Check if PDF exists for a reservation."""
    reservation = db.query(Reservation).filter(
        Reservation.id == reservation_id,
        Reservation.groom_id == current.id
    ).first()

    if not reservation:
        raise HTTPException(404, "الحجز غير موجود")

    pdf_exists = bool(
        reservation.pdf_url and os.path.exists(reservation.pdf_url)
    )

    return {
        "reservation_id": reservation_id,
        "pdf_exists": pdf_exists,
        "pdf_url": f"/pdf/download/{reservation.id}" if pdf_exists else None
    }
