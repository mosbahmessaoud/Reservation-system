# # app/utils/pdf_generator.py
# from docx import Document
# import os
# import subprocess
# from datetime import datetime

# from server.models.clan import Clan
# from server.models.committee import HaiaCommittee, MadaehCommittee
# from server.models.county import County
# from server.models.user import User


# def replace_placeholder_in_runs(runs, key, value):
#     """Replace placeholder text inside runs while preserving formatting."""
#     placeholder = f"{{{{{key}}}}}"
#     # Merge all run text into one string
#     full_text = "".join(run.text for run in runs)
#     if placeholder in full_text:
#         full_text = full_text.replace(placeholder, str(value or ""))
#         # Clear all runs first
#         for run in runs:
#             run.text = ""
#         # Put replaced text back into first run
#         runs[0].text = full_text


# def fill_docx_template(template_path: str, output_path: str, context: dict):
#     doc = Document(template_path)

#     # Replace in paragraphs
#     for p in doc.paragraphs:
#         for key, value in context.items():
#             replace_placeholder_in_runs(p.runs, key, value)

#     # Replace in tables
#     for table in doc.tables:
#         for row in table.rows:
#             for cell in row.cells:
#                 for p in cell.paragraphs:
#                     for key, value in context.items():
#                         replace_placeholder_in_runs(p.runs, key, value)

#     doc.save(output_path)


# def convert_to_pdf(docx_path: str, pdf_path: str):
#     try:
#         from docx2pdf import convert
#         convert(docx_path, pdf_path)
#     except Exception:
#         subprocess.run([
#             "libreoffice", "--headless", "--convert-to", "pdf", "--outdir",
#             os.path.dirname(pdf_path), docx_path
#         ], check=True)


# def generate_wedding_pdf(reservation, output_dir: str, db):
#     os.makedirs(output_dir, exist_ok=True)

#     template_path = "app/templates/wedding_request_form.docx"
#     filled_docx_path = os.path.join(
#         output_dir, f"reservation_{reservation.id}.docx")
#     pdf_path = os.path.join(output_dir, f"reservation_{reservation.id}.pdf")

#     # Get DB values
#     user_of_this_reservation = db.query(User).filter(
#         User.id == reservation.groom_id).first()
#     reserved_clan = db.query(Clan).filter(
#         Clan.id == reservation.clan_id).first()
#     oringi_clan = db.query(Clan).filter(
#         Clan.id == user_of_this_reservation.clan_id).first()
#     county = db.query(County).filter(
#         County.id == user_of_this_reservation.county_id).first()
#     haia_committee_id = db.query(HaiaCommittee).filter(
#         HaiaCommittee.id == reservation.haia_committee_id).first()
#     madaeh_committee_id = db.query(MadaehCommittee).filter(
#         MadaehCommittee.id == reservation.madaeh_committee_id).first()

#     context = {
#         "COUNTY": county.name,
#         "ORIGIN_CLAN": oringi_clan.name,
#         "RESERVED_CLAN": reserved_clan.name,
#         "groom_NAME": user_of_this_reservation.first_name,
#         "last_name": user_of_this_reservation.last_name,
#         "GUARDIAN_NAME": user_of_this_reservation.guardian_name,
#         "father_name": user_of_this_reservation.father_name,
#         "guardian_birth_date": user_of_this_reservation.guardian_birth_date,
#         "guardian_birth_address": user_of_this_reservation.guardian_birth_address,
#         "guardian_home_address": user_of_this_reservation.guardian_home_address,
#         "grandfather_name": user_of_this_reservation.grandfather_name,
#         "birth_date": user_of_this_reservation.birth_date.strftime("%Y-%m-%d") if user_of_this_reservation.birth_date else "",
#         "birth_address": user_of_this_reservation.birth_address,
#         "home_address": user_of_this_reservation.home_address,
#         "phone_number": user_of_this_reservation.phone_number,
#         "WEDDING_DATES": f"{reservation.date1.strftime('%Y-%m-%d')} - {reservation.date2.strftime('%Y-%m-%d')}" if reservation.date2 else reservation.date1.strftime("%Y-%m-%d"),
#         "haia_committee_id": haia_committee_id.name if haia_committee_id else "",
#         "madaeh_committee_id": madaeh_committee_id.name if madaeh_committee_id else "",
#         "GUARDIAN_phone": user_of_this_reservation.guardian_phone,
#         "created_at": reservation.created_at.strftime("%Y-%m-%d") if reservation.created_at else "",
#     }

#     # Fill and generate PDF
#     fill_docx_template(template_path, filled_docx_path, context)
#     convert_to_pdf(filled_docx_path, pdf_path)

#     return pdf_path
