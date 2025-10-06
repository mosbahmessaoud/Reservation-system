"""
Simplified PDF generation and download routes.
"""
import tempfile
import shutil
from typing import Optional
from pathlib import Path
import uuid
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import APIRouter, File, UploadFile, HTTPException, Request
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


# ⚠️ IMPORTANT: Railway uses ephemeral storage
# Files will be lost on redeploy. For persistent storage, use:
# - Railway Volumes (recommended)
# - External storage (AWS S3, Cloudflare R2, etc.)

# For Railway Volumes, mount to /data
RAILWAY_VOLUME_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/data")
UPLOAD_DIR = Path(RAILWAY_VOLUME_PATH) / "uploads" / "pdfs"

# Fallback to temp directory if volume not available
if not os.path.exists(RAILWAY_VOLUME_PATH):
    UPLOAD_DIR = Path(tempfile.gettempdir()) / "uploads" / "pdfs"
    print(
        f"⚠️ WARNING: Using temp directory {UPLOAD_DIR}. Files will be deleted on redeploy!")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf"}

# Store file metadata in memory (use database in production)
file_metadata = {}


@router.post("/pdf")
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    """
    Upload a PDF file to Railway

    Returns:
        {
            "success": true,
            "url": "https://your-railway-app.railway.app/api/upload/pdf/{file_id}",
            "filename": "original_filename.pdf",
            "file_id": "unique_file_id",
            "size": 12345
        }
    """
    try:
        # Validate file type
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Only PDF files are allowed."
            )

        # Validate file size
        content = await file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024)}MB"
            )

        # Generate unique file ID
        file_id = str(uuid.uuid4())
        unique_filename = f"{file_id}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # Store metadata
        file_metadata[file_id] = {
            "original_filename": file.filename,
            "filename": unique_filename,
            "size": file_size,
            "content_type": "application/pdf"
        }

        # Get the base URL from request
        base_url = str(request.base_url).rstrip('/')

        # Generate URL for file access
        file_url = f"{base_url}/api/upload/pdf/{file_id}"

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "url": file_url,
                "filename": file.filename,
                "file_id": file_id,
                "size": file_size
            }
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )


@router.get("/pdf/{file_id}")
async def get_pdf(file_id: str):
    """
    Retrieve a PDF file by its ID
    """
    try:
        # Check if file exists in metadata
        if file_id not in file_metadata:
            raise HTTPException(
                status_code=404,
                detail="File not found"
            )

        metadata = file_metadata[file_id]
        file_path = UPLOAD_DIR / metadata["filename"]

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail="File not found on disk"
            )

        # Return file as streaming response
        def iterfile():
            with open(file_path, mode="rb") as file_like:
                yield from file_like

        return StreamingResponse(
            iterfile(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{metadata["original_filename"]}"'
            }
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving file: {str(e)}"
        )


@router.delete("/pdf/{file_id}")
async def delete_pdf(file_id: str):
    """
    Delete a PDF file by its ID
    """
    try:
        # Check if file exists in metadata
        if file_id not in file_metadata:
            raise HTTPException(
                status_code=404,
                detail="File not found"
            )

        metadata = file_metadata[file_id]
        file_path = UPLOAD_DIR / metadata["filename"]

        # Delete file from disk
        if file_path.exists():
            os.remove(file_path)

        # Remove from metadata
        del file_metadata[file_id]

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "File deleted successfully"
            }
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting file: {str(e)}"
        )


# pdf generater#################


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
