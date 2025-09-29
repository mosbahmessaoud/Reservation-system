# # routes/pdf_routes.py
# from fastapi import APIRouter, HTTPException
# from fastapi.responses import FileResponse
# from utils.pdf_generator.py import generate_wedding_pdf
# import os
# from database import get_reservation_by_id  # your DB query

# router = APIRouter()

# TEMPLATE_PATH = "templates/wedding_request_form.docx"
# OUTPUT_DIR = "generated_pdfs"

# @router.get("/reservations/{reservation_id}/pdf")
# def generate_reservation_pdf(reservation_id: int):
#     # Get data from DB
#     reservation = get_reservation_by_id(reservation_id)
#     if not reservation:
#         raise HTTPException(status_code=404, detail="Reservation not found")

#     # Build context for placeholders
#     context = {
#         "COUNTY": reservation.county.name,
#         "CLAN": reservation.clan.name,
#         "GUARDIAN_NAME": reservation.guardian_name,
#         "father_name": reservation.father_name,
#         "grandfather_name": reservation.grandfather_name,
#         "birth_date": reservation.birth_date.strftime("%Y-%m-%d"),
#         "birth_address": reservation.birth_address,
#         "home_address": reservation.home_address,
#         "phone_number": reservation.phone_number,
#         "WEDDING_DATES": ", ".join([d.strftime("%Y-%m-%d") for d in reservation.dates]),
#         "haia_committee_id": reservation.haia_committee.name,
#         "madaeh_committee_id": reservation.madaeh_committee.name,
#         "GUARDIAN_phone": reservation.guardian_phone,
#         "created_at": reservation.created_at.strftime("%Y-%m-%d"),
#     }

#     pdf_path = generate_wedding_pdf(TEMPLATE_PATH, OUTPUT_DIR, context)
#     return FileResponse(pdf_path, filename="wedding_reservation.pdf", media_type="application/pdf")
