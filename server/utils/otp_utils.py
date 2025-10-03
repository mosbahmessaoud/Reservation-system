#server\utils\otp_utils.py
import random
from twilio.rest import Client
import os

from server.utils.phone_utils import validate_algerian_number

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")


def generate_otp_code(length: int = 6) -> str:
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


def send_otp_to_user_by_twilo(phone_number: str, code: str):
    phone_number = validate_algerian_number(phone_number)
    if not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_PHONE:
        raise ValueError("Twilio configuration is not set properly.")
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    message = f"Your code is {code}"  # ✅ More likely to go through
    client.messages.create(
        body=message,
        from_=TWILIO_PHONE,
        to=phone_number
    )
