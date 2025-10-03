"""
PDF generation and download routes for reservations.
"""
import logging
import subprocess
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from server.utils.pdf_generator import generate_wedding_pdf, test_pdf_generation
from server.models.reservation import Reservation, ReservationStatus
from ..auth_utils import get_current_user, get_db, require_role
from ..models.user import User, UserRole

router = APIRouter(
    prefix="/pdf",
    tags=["pdf"]
)

# groom_required = require_role([UserRole.groom])
clan_admin_required = require_role([UserRole.clan_admin])

# Add logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.post("/generate/{reservation_id}")
def generate_pdf(
    reservation_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Generate PDF for a specific reservation.
    Can be called independently after reservation creation.
    """
    try:
        # Get the reservation
        reservation = db.query(Reservation).filter(
            Reservation.id == reservation_id,
            Reservation.groom_id == current.id
        ).first()

        if not reservation:
            raise HTTPException(404, "الحجز غير موجود")

        # Check if PDF already exists
        if reservation.pdf_url:
            return {
                "message": "PDF موجود بالفعل",
                "pdf_url": f"/pdf/download/{reservation.id}",
                "regenerated": False
            }

        # Test PDF generation capabilities
        try:
            test_result = test_pdf_generation()
            if not test_result:
                logger.warning("PDF generation test failed")
                raise HTTPException(500, "نظام إنشاء PDF غير متاح حالياً")
        except Exception as e:
            logger.error(f"PDF generation test error: {e}")
            raise HTTPException(500, f"خطأ في اختبار نظام PDF: {str(e)}")

        # Generate PDF
        logger.info(
            f"Starting PDF generation for reservation {reservation_id}")

        try:
            pdf_path = generate_wedding_pdf(
                reservation,
                output_dir="generated_pdfs",
                db=db
            )

            if not pdf_path:
                raise Exception("PDF path is None")

            # Update reservation with PDF path
            reservation.pdf_url = pdf_path
            db.commit()

            logger.info(f"PDF successfully generated: {pdf_path}")

            return {
                "message": "تم إنشاء PDF بنجاح",
                "pdf_url": f"/pdf/download/{reservation.id}",
                "regenerated": False
            }

        except FileNotFoundError as e:
            error_msg = f"Template or LibreOffice not found: {str(e)}"
            logger.error(
                f"PDF generation failed - FileNotFoundError: {error_msg}")
            raise HTTPException(500, "ملفات النظام المطلوبة غير موجودة")

        except subprocess.TimeoutExpired:
            error_msg = "PDF conversion timed out"
            logger.error(f"PDF generation failed - Timeout: {error_msg}")
            raise HTTPException(500, "انتهت مهلة إنشاء PDF")

        except ImportError as e:
            error_msg = f"Required PDF library not installed: {str(e)}"
            logger.error(f"PDF generation failed - ImportError: {error_msg}")
            raise HTTPException(500, "مكتبات PDF المطلوبة غير مثبتة")

        except Exception as e:
            error_msg = f"Unexpected PDF generation error: {str(e)}"
            logger.error(f"PDF generation failed - General error: {error_msg}")
            raise HTTPException(500, f"خطأ غير متوقع في إنشاء PDF: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_pdf: {e}")
        raise HTTPException(500, f"خطأ غير متوقع: {str(e)}")


@router.post("/regenerate/{reservation_id}")
def regenerate_pdf(
    reservation_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Force regenerate PDF for a specific reservation (overwrites existing).
    """
    try:
        # Get the reservation
        reservation = db.query(Reservation).filter(
            Reservation.id == reservation_id,
            Reservation.groom_id == current.id
        ).first()

        if not reservation:
            raise HTTPException(404, "الحجز غير موجود")

        # Test PDF generation capabilities
        try:
            test_result = test_pdf_generation()
            if not test_result:
                raise HTTPException(500, "نظام إنشاء PDF غير متاح حالياً")
        except Exception as e:
            logger.error(f"PDF generation test error: {e}")
            raise HTTPException(500, f"خطأ في اختبار نظام PDF: {str(e)}")

        # Generate PDF (overwrite existing)
        logger.info(f"Regenerating PDF for reservation {reservation_id}")

        try:
            pdf_path = generate_wedding_pdf(
                reservation,
                output_dir="generated_pdfs",
                db=db
            )

            if not pdf_path:
                raise Exception("PDF path is None")

            # Update reservation with new PDF path
            reservation.pdf_url = pdf_path
            db.commit()

            logger.info(f"PDF successfully regenerated: {pdf_path}")

            return {
                "message": "تم إعادة إنشاء PDF بنجاح",
                "pdf_url": f"/pdf/download/{reservation.id}",
                "regenerated": True
            }

        except Exception as e:
            error_msg = f"PDF regeneration error: {str(e)}"
            logger.error(f"PDF regeneration failed: {error_msg}")
            raise HTTPException(500, f"خطأ في إعادة إنشاء PDF: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in regenerate_pdf: {e}")
        raise HTTPException(500, f"خطأ غير متوقع: {str(e)}")


@router.get("/download/{reservation_id}")
def download_pdf(
    reservation_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Download PDF for a specific reservation.
    Accessible by groom or clan admin.
    """
    try:
        # Get the reservation
        reservation = db.query(Reservation).filter(
            Reservation.id == reservation_id
        ).first()

        if not reservation:
            raise HTTPException(404, "الحجز غير موجود")

        # Check permissions
        is_groom = current.id == reservation.groom_id
        is_clan_admin = (
            current.role == UserRole.clan_admin and
            current.clan_id == reservation.clan_id
        )

        if not (is_groom or is_clan_admin):
            raise HTTPException(403, "غير مصرح لك بتحميل هذا الملف")

        # Check if PDF exists
        if not reservation.pdf_url:
            raise HTTPException(
                404, "ملف PDF غير موجود.  ")

        # Return the PDF file
        import os
        if not os.path.exists(reservation.pdf_url):
            logger.error(f"PDF file not found at path: {reservation.pdf_url}")
            raise HTTPException(404, "ملف PDF غير موجود على الخادم")

        return FileResponse(
            reservation.pdf_url,
            media_type="application/pdf",
            filename=f"reservation_{reservation_id}.pdf"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in download_pdf: {e}")
        raise HTTPException(500, f"خطأ غير متوقع: {str(e)}")


@router.get("/status/{reservation_id}")
def check_pdf_status(
    reservation_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Check if PDF exists for a reservation.
    """
    try:
        reservation = db.query(Reservation).filter(
            Reservation.id == reservation_id,
            Reservation.groom_id == current.id
        ).first()

        if not reservation:
            raise HTTPException(404, "الحجز غير موجود")

        import os
        pdf_exists = bool(
            reservation.pdf_url and os.path.exists(reservation.pdf_url))

        return {
            "reservation_id": reservation_id,
            "pdf_exists": pdf_exists,
            "pdf_url": f"/pdf/download/{reservation.id}" if pdf_exists else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in check_pdf_status: {e}")
        raise HTTPException(500, f"خطأ غير متوقع: {str(e)}")
