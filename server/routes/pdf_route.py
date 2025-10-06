"""
Simplified PDF generation and download routes.
"""
from ..auth_utils import get_db
from fastapi import APIRouter, File, UploadFile, HTTPException, Request, Depends
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
"""
PDF upload/download routes with Railway Volume support
"""


router = APIRouter(prefix="/pdf", tags=["pdf"])
logger = logging.getLogger(__name__)

# Railway Volume Configuration
# In Railway, set environment variable: RAILWAY_VOLUME_MOUNT_PATH=/data
RAILWAY_VOLUME_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/data")
UPLOAD_DIR = Path(RAILWAY_VOLUME_PATH) / "uploads" / "pdfs"

# Fallback to temp directory if volume not available (for local development)
if not os.path.exists(RAILWAY_VOLUME_PATH):
    UPLOAD_DIR = Path(tempfile.gettempdir()) / "uploads" / "pdfs"
    logger.warning(
        f"Using temp directory {UPLOAD_DIR}. Files will be deleted on restart!")
else:
    logger.info(f"Using Railway volume at {UPLOAD_DIR}")

# Create upload directory
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf"}


# Database model for file metadata (add this to your models)
# You'll need to create this model and migration
"""
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String, unique=True, index=True, nullable=False)
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String, default="application/pdf")
    upload_date = Column(DateTime, default=datetime.utcnow)
    
    # Optional: Link to user or clan
    # uploaded_by_user_id = Column(Integer, ForeignKey("users.id"))
    # clan_id = Column(Integer, ForeignKey("clans.id"))
"""

# Temporary in-memory storage (until you create the database model)
file_metadata = {}


@router.post("/api/upload/pdf/")
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="يُسمح فقط بملفات PDF"
            )

        # Read and validate file size
        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(status_code=400, detail="الملف فارغ")

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"حجم الملف كبير جداً. الحد الأقصى هو {MAX_FILE_SIZE / (1024*1024):.0f} ميجابايت"
            )

        # Generate unique file ID and filename
        file_id = str(uuid.uuid4())
        unique_filename = f"{file_id}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        # Save file to volume
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            logger.info(f"File saved: {unique_filename} ({file_size} bytes)")
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"فشل حفظ الملف: {str(e)}"
            )

        # Store metadata (use database in production)
        # TODO: Replace with database storage
        file_metadata[file_id] = {
            "original_filename": file.filename,
            "stored_filename": unique_filename,
            "size": file_size,
            "content_type": "application/pdf"
        }

        # If you have the UploadedFile model, use this instead:
        # from server.models.uploaded_file import UploadedFile
        # db_file = UploadedFile(
        #     file_id=file_id,
        #     original_filename=file.filename,
        #     stored_filename=unique_filename,
        #     file_size=file_size,
        #     content_type="application/pdf"
        # )
        # db.add(db_file)
        # db.commit()

        # Generate URL for file access - FIX THIS LINE
        base_url = str(request.base_url).rstrip('/')
        # Added /pdf prefix
        file_url = f"{base_url}/pdf/api/upload/pdf/{file_id}"

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في تحميل الملف: {str(e)}"
        )


@router.get("/api/upload/pdf/{file_id}")
async def get_pdf(file_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a PDF file by its ID

    Args:
        file_id: Unique file identifier

    Returns:
        PDF file as streaming response
    """
    try:
        # Get metadata from memory (or database)
        if file_id not in file_metadata:
            raise HTTPException(status_code=404, detail="الملف غير موجود")

        # If using database:
        # from server.models.uploaded_file import UploadedFile
        # db_file = db.query(UploadedFile).filter(UploadedFile.file_id == file_id).first()
        # if not db_file:
        #     raise HTTPException(status_code=404, detail="الملف غير موجود")
        # metadata = {
        #     "stored_filename": db_file.stored_filename,
        #     "original_filename": db_file.original_filename
        # }

        metadata = file_metadata[file_id]
        file_path = UPLOAD_DIR / metadata["stored_filename"]

        if not file_path.exists():
            logger.error(f"File not found on disk: {file_path}")
            raise HTTPException(
                status_code=404, detail="الملف غير موجود على الخادم")

        # Return file as streaming response
        def iterfile():
            with open(file_path, mode="rb") as file_like:
                yield from file_like

        return StreamingResponse(
            iterfile(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{metadata["original_filename"]}"',
                "Cache-Control": "public, max-age=3600"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في استرجاع الملف: {str(e)}"
        )


@router.delete("/api/upload/pdf/{file_id}")
async def delete_pdf(file_id: str, db: Session = Depends(get_db)):
    """
    Delete a PDF file by its ID

    Args:
        file_id: Unique file identifier

    Returns:
        Success message
    """
    try:
        # Check metadata
        if file_id not in file_metadata:
            raise HTTPException(status_code=404, detail="الملف غير موجود")

        # If using database:
        # from server.models.uploaded_file import UploadedFile
        # db_file = db.query(UploadedFile).filter(UploadedFile.file_id == file_id).first()
        # if not db_file:
        #     raise HTTPException(status_code=404, detail="الملف غير موجود")

        metadata = file_metadata[file_id]
        file_path = UPLOAD_DIR / metadata["stored_filename"]

        # Delete file from disk
        if file_path.exists():
            try:
                os.remove(file_path)
                logger.info(f"File deleted: {metadata['stored_filename']}")
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"فشل حذف الملف: {str(e)}"
                )

        # Remove from metadata
        del file_metadata[file_id]

        # If using database:
        # db.delete(db_file)
        # db.commit()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "تم حذف الملف بنجاح"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في حذف الملف: {str(e)}"
        )


@router.get("/api/upload/health")
async def check_storage():
    """
    Check storage health and availability
    """
    try:
        volume_exists = os.path.exists(RAILWAY_VOLUME_PATH)
        upload_dir_exists = UPLOAD_DIR.exists()

        # Count files
        file_count = len(list(UPLOAD_DIR.glob("*.pdf"))
                         ) if upload_dir_exists else 0

        # Get directory size
        total_size = 0
        if upload_dir_exists:
            for file in UPLOAD_DIR.glob("*.pdf"):
                total_size += file.stat().st_size

        return {
            "status": "healthy",
            "volume_mounted": volume_exists,
            "upload_dir_exists": upload_dir_exists,
            "upload_dir_path": str(UPLOAD_DIR),
            "files_stored": file_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
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
