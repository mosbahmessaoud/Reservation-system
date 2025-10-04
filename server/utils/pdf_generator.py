# app/utils/pdf_generator.py
from docx import Document
import os
import subprocess
import sys
import logging
from datetime import datetime
from pathlib import Path

from server.models.clan import Clan
from server.models.committee import HaiaCommittee, MadaehCommittee
from server.models.county import County
from server.models.user import User

logger = logging.getLogger(__name__)


def replace_placeholder_in_runs(runs, key, value):
    """Replace placeholder text inside runs while preserving formatting."""
    placeholder = f"{{{{{key}}}}}"
    # Merge all run text into one string
    full_text = "".join(run.text for run in runs)
    if placeholder in full_text:
        full_text = full_text.replace(placeholder, str(value or ""))
        # Clear all runs first
        for run in runs:
            run.text = ""
        # Put replaced text back into first run
        runs[0].text = full_text


def fill_docx_template(template_path: str, output_path: str, context: dict):
    """Fill DOCX template with context data."""
    try:
        doc = Document(template_path)

        # Replace in paragraphs
        for p in doc.paragraphs:
            for key, value in context.items():
                replace_placeholder_in_runs(p.runs, key, value)

        # Replace in tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        for key, value in context.items():
                            replace_placeholder_in_runs(p.runs, key, value)

        doc.save(output_path)
        logger.info(f"Successfully filled DOCX template: {output_path}")
    except Exception as e:
        logger.error(f"Error filling DOCX template: {e}")
        raise


def find_libreoffice():
    """Find LibreOffice executable path."""
    possible_paths = [
        "libreoffice",  # Linux/Mac in PATH
        "/usr/bin/libreoffice",  # Linux
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",  # Mac
        r"C:\Program Files\LibreOffice\program\soffice.exe",  # Windows
        # Windows 32-bit
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    for path in possible_paths:
        try:
            result = subprocess.run([path, "--version"],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"Found LibreOffice at: {path}")
                return path
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue

    return None


def convert_to_pdf(docx_path: str, pdf_path: str):
    """Convert DOCX to PDF using LibreOffice."""
    docx_path = Path(docx_path).resolve()
    pdf_path = Path(pdf_path).resolve()

    # Ensure output directory exists
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Converting DOCX to PDF...")
    logger.info(f"  Input: {docx_path}")
    logger.info(f"  Output: {pdf_path}")

    # Find LibreOffice
    libreoffice_path = find_libreoffice()
    if not libreoffice_path:
        raise Exception("LibreOffice not found. Please install LibreOffice.")

    try:
        # Use LibreOffice to convert
        # Output will be created in the same directory as input with .pdf extension
        cmd = [
            libreoffice_path,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(pdf_path.parent),
            str(docx_path)
        ]

        logger.info(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # Increased timeout to 2 minutes
        )

        # Log the output for debugging
        if result.stdout:
            logger.info(f"LibreOffice stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"LibreOffice stderr: {result.stderr}")

        # LibreOffice creates the PDF with the same base name as the DOCX
        expected_pdf = pdf_path.parent / f"{docx_path.stem}.pdf"

        logger.info(f"Expected PDF location: {expected_pdf}")
        logger.info(f"Target PDF location: {pdf_path}")

        # Check if conversion was successful
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise Exception(f"LibreOffice conversion failed: {error_msg}")

        # Wait a moment for file system to sync
        import time
        time.sleep(1)

        # If the expected PDF location is different from target, move it
        if expected_pdf != pdf_path:
            if expected_pdf.exists():
                import shutil
                shutil.move(str(expected_pdf), str(pdf_path))
                logger.info(f"Moved PDF from {expected_pdf} to {pdf_path}")
            else:
                raise Exception(
                    f"PDF was not created at expected location: {expected_pdf}")

        # Final verification
        if not pdf_path.exists():
            raise Exception(f"PDF file was not created at: {pdf_path}")

        logger.info(f"Successfully converted to PDF: {pdf_path}")

    except subprocess.TimeoutExpired:
        logger.error("LibreOffice conversion timed out")
        raise Exception("PDF conversion timed out (exceeded 2 minutes)")
    except Exception as e:
        logger.error(f"LibreOffice conversion error: {e}")
        raise Exception(f"PDF conversion failed: {str(e)}")


def find_libreoffice():
    """Find LibreOffice executable path."""
    possible_paths = [
        "libreoffice",  # Linux in PATH
        "/usr/bin/libreoffice",  # Linux standard location
        "/usr/bin/soffice",  # Alternative Linux location
        "soffice",  # Linux in PATH
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",  # Mac
        r"C:\Program Files\LibreOffice\program\soffice.exe",  # Windows
        # Windows 32-bit
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    for path in possible_paths:
        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Found LibreOffice at: {path}")
                logger.info(f"Version: {result.stdout.strip()}")
                return path
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue

    logger.error("LibreOffice not   found in any standard location")
    return None


def find_template_path():

    # Get the directory where pdf_generator.py is located (server/utils/)
    current_file_dir = Path(__file__).parent  # server/utils/

    # Go up one level to server/, then navigate to app/templates/
    server_dir = current_file_dir.parent  # server/
    template_path = server_dir / "app" / "templates" / "wedding_request_form.docx"

    if template_path.exists():
        logger.info(f"Found template at: {template_path.resolve()}")
        return str(template_path.resolve())

    # Fallback: Log the issue for debugging
    logger.error(
        f"Template not found at expected path: {template_path.resolve()}")
    logger.error(f"Current file location: {Path(__file__).resolve()}")
    logger.error(f"Server directory: {server_dir.resolve()}")

    raise FileNotFoundError(
        f"wedding_request_form.docx not found at {template_path.resolve()}"
    )


def generate_wedding_pdf(reservation, output_dir: str, db):
    """Generate wedding PDF from reservation data."""
    try:
        # Ensure output directory exists
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find template
        template_path = find_template_path()

        # Generate unique file paths with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = f"{reservation.id}_{timestamp}"

        filled_docx_path = output_dir / f"reservation_{unique_id}_filled.docx"
        pdf_path = output_dir / f"reservation_{unique_id}.pdf"

        logger.info(f"Generating PDF for reservation {reservation.id}")
        logger.info(f"Template: {template_path}")
        logger.info(f"DOCX output: {filled_docx_path}")
        logger.info(f"PDF output: {pdf_path}")

        # Get database values with error handling
        try:
            user_of_this_reservation = db.query(User).filter(
                User.id == reservation.groom_id).first()
            if not user_of_this_reservation:
                raise Exception(
                    f"User not found for groom_id: {reservation.groom_id}")

            reserved_clan = db.query(Clan).filter(
                Clan.id == reservation.clan_id).first()
            if not reserved_clan:
                raise Exception(
                    f"Reserved clan not found: {reservation.clan_id}")

            original_clan = db.query(Clan).filter(
                Clan.id == user_of_this_reservation.clan_id).first()
            if not original_clan:
                raise Exception(
                    f"Original clan not found: {user_of_this_reservation.clan_id}")

            county = db.query(County).filter(
                County.id == user_of_this_reservation.county_id).first()
            if not county:
                raise Exception(
                    f"County not found: {user_of_this_reservation.county_id}")

            haia_committee = db.query(HaiaCommittee).filter(
                HaiaCommittee.id == reservation.haia_committee_id).first()

            madaeh_committee = db.query(MadaehCommittee).filter(
                MadaehCommittee.id == reservation.madaeh_committee_id).first()

        except Exception as e:
            logger.error(f"Database query error: {e}")
            raise Exception(f"Failed to fetch required data: {e}")

        # Prepare context data
        context = {
            "COUNTY": county.name if county else "",
            "ORIGIN_CLAN": original_clan.name if original_clan else "",
            "RESERVED_CLAN": reserved_clan.name if reserved_clan else "",
            "groom_NAME": user_of_this_reservation.first_name or "",
            "last_name": user_of_this_reservation.last_name or "",
            "GUARDIAN_NAME": user_of_this_reservation.guardian_name or "",
            "father_name": user_of_this_reservation.father_name or "",
            "guardian_birth_date": user_of_this_reservation.guardian_birth_date.strftime("%Y-%m-%d") if user_of_this_reservation.guardian_birth_date else "",
            "guardian_birth_address": user_of_this_reservation.guardian_birth_address or "",
            "guardian_home_address": user_of_this_reservation.guardian_home_address or "",
            "grandfather_name": user_of_this_reservation.grandfather_name or "",
            "birth_date": user_of_this_reservation.birth_date.strftime("%Y-%m-%d") if user_of_this_reservation.birth_date else "",
            "birth_address": user_of_this_reservation.birth_address or "",
            "home_address": user_of_this_reservation.home_address or "",
            "phone_number": user_of_this_reservation.phone_number or "",
            "WEDDING_DATES": f"{reservation.date1.strftime('%Y-%m-%d')} - {reservation.date2.strftime('%Y-%m-%d')}" if reservation.date2 else reservation.date1.strftime("%Y-%m-%d"),
            "haia_committee_id": haia_committee.name if haia_committee else "",
            "madaeh_committee_id": madaeh_committee.name if madaeh_committee else "",
            "GUARDIAN_phone": user_of_this_reservation.guardian_phone or "",
            "created_at": reservation.created_at.strftime("%Y-%m-%d") if reservation.created_at else "",
        }

        # Fill DOCX template
        fill_docx_template(template_path, str(filled_docx_path), context)

        # Verify DOCX was created
        if not filled_docx_path.exists():
            raise Exception("DOCX file was not created successfully")

        logger.info(f"DOCX created successfully: {filled_docx_path}")

        # Convert to PDF
        convert_to_pdf(str(filled_docx_path), str(pdf_path))

        # Verify PDF was created
        if not pdf_path.exists():
            raise Exception("PDF file was not created successfully")

        logger.info(f"Successfully generated PDF: {pdf_path}")

        # Always clean up the intermediate DOCX file
        try:
            if filled_docx_path.exists():
                filled_docx_path.unlink()
                logger.info(
                    f"Cleaned up intermediate DOCX file: {filled_docx_path}")
        except Exception as e:
            logger.warning(f"Could not delete intermediate DOCX: {e}")

        return str(pdf_path)

    except Exception as e:
        logger.error(
            f"PDF generation failed for reservation {reservation.id}: {e}")
        # Clean up any partial files
        try:
            if 'filled_docx_path' in locals() and filled_docx_path.exists():
                filled_docx_path.unlink()
                logger.info("Cleaned up partial DOCX file")
            if 'pdf_path' in locals() and pdf_path.exists():
                pdf_path.unlink()
                logger.info("Cleaned up partial PDF file")
        except Exception as cleanup_error:
            logger.warning(f"Cleanup error: {cleanup_error}")

        raise Exception(f"PDF generation failed: {e}")


# Additional utility function for testing
def test_pdf_generation():
    """Test PDF generation capabilities."""
    print("Testing PDF generation capabilities...")

    # Test template
    try:
        template_path = find_template_path()
        print(f"✓ Template found: {template_path}")
    except Exception as e:
        print(f"✗ Template not found: {e}")
        return False

    # Test LibreOffice
    libreoffice_path = find_libreoffice()
    if libreoffice_path:
        print(f"✓ LibreOffice found: {libreoffice_path}")
    else:
        print("✗ LibreOffice not found")

    # Test docx2pdf
    try:
        import docx2pdf
        print("✓ docx2pdf available")
    except ImportError:
        print("✗ docx2pdf not available")

    return True


if __name__ == "__main__":
    test_pdf_generation()
