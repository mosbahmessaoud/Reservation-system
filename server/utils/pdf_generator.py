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
    """Convert DOCX to PDF using available methods."""
    docx_path = Path(docx_path).resolve()
    pdf_path = Path(pdf_path).resolve()

    # Ensure output directory exists
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # Method 1: Try docx2pdf with COM initialization
    try:
        import pythoncom
        pythoncom.CoInitialize()  # Add this line
        try:
            from docx2pdf import convert
            convert(str(docx_path), str(pdf_path))
            logger.info(
                f"Successfully converted to PDF using docx2pdf: {pdf_path}")
            return
        finally:
            pythoncom.CoUninitialize()  # Add this line
    except ImportError:
        logger.info("docx2pdf not available, trying LibreOffice...")
    except Exception as e:
        logger.warning(f"docx2pdf failed: {e}, trying LibreOffice...")

    # Method 2: Try LibreOffice
    libreoffice_path = find_libreoffice()
    if libreoffice_path:
        try:
            cmd = [
                libreoffice_path,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(pdf_path.parent),
                str(docx_path)
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0 and pdf_path.exists():
                logger.info(
                    f"Successfully converted to PDF using LibreOffice: {pdf_path}")
                return
            else:
                logger.error(f"LibreOffice conversion failed: {result.stderr}")
                raise Exception(
                    f"LibreOffice conversion failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.error("LibreOffice conversion timed out")
            raise Exception("LibreOffice conversion timed out")
        except Exception as e:
            logger.error(f"LibreOffice conversion error: {e}")
            raise

    # Method 3: Fallback - just copy the DOCX file with PDF extension
    # This is a last resort and won't be a real PDF
    logger.warning("No PDF conversion method available, copying DOCX file")
    import shutil
    shutil.copy2(docx_path, pdf_path.with_suffix('.docx'))
    raise Exception(
        "No PDF conversion method available. Please install LibreOffice or docx2pdf.")


def find_template_path():
    """Find the wedding request form template."""
    possible_paths = [
        "app/templates/wedding_request_form.docx",
        "server/templates/wedding_request_form.docx",
        "templates/wedding_request_form.docx",
        "../templates/wedding_request_form.docx",
        "wedding_request_form.docx"
    ]

    for path in possible_paths:
        full_path = Path(path).resolve()
        if full_path.exists():
            logger.info(f"Found template at: {full_path}")
            return str(full_path)

    # Try relative to current file
    current_dir = Path(__file__).parent
    template_path = current_dir.parent / "templates" / "wedding_request_form.docx"
    if template_path.exists():
        logger.info(f"Found template at: {template_path}")
        return str(template_path)

    logger.error("Template file not found in any expected location")
    raise FileNotFoundError("wedding_request_form.docx template not found")


def generate_wedding_pdf(reservation, output_dir: str, db):
    """Generate wedding PDF from reservation data."""
    try:
        # Ensure output directory exists
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find template
        template_path = find_template_path()

        # Generate file paths
        filled_docx_path = output_dir / f"reservation_{reservation.id}.docx"
        pdf_path = output_dir / f"reservation_{reservation.id}.pdf"

        logger.info(f"Generating PDF for reservation {reservation.id}")
        logger.info(f"Template: {template_path}")
        logger.info(f"Output: {pdf_path}")

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

        # Convert to PDF
        convert_to_pdf(str(filled_docx_path), str(pdf_path))

        # Verify PDF was created
        if not pdf_path.exists():
            raise Exception("PDF file was not created successfully")

        logger.info(f"Successfully generated PDF: {pdf_path}")
        return str(pdf_path)

    except Exception as e:
        logger.error(
            f"PDF generation failed for reservation {reservation.id}: {e}")
        # Clean up any partial files
        try:
            if 'filled_docx_path' in locals() and filled_docx_path.exists():
                filled_docx_path.unlink()
            if 'pdf_path' in locals() and pdf_path.exists():
                pdf_path.unlink()
        except:
            pass
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
