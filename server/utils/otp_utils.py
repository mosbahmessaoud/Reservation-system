
# server/utils/otp_utils.py
import secrets
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import os
import logging
from datetime import datetime, timedelta

from server.utils.phone_utils import validate_algerian_number

logger = logging.getLogger(__name__)

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

# Simple in-memory rate limiting (good for 100 users)
otp_attempts = {}


def generate_otp_code(length: int = 6) -> str:
    """Generate secure random OTP"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(length)])


def check_rate_limit(phone_number: str) -> bool:
    """
    Simple rate limiting: max 3 requests per hour
    For 100 users, in-memory storage is fine
    """
    current_time = datetime.utcnow()

    if phone_number in otp_attempts:
        last_attempt, count = otp_attempts[phone_number]

        # Reset counter after 1 hour
        if current_time - last_attempt > timedelta(hours=1):
            otp_attempts[phone_number] = (current_time, 1)
            return True

        # Check if exceeded 3 attempts
        if count >= 3:
            return False

        # Increment counter
        otp_attempts[phone_number] = (last_attempt, count + 1)
    else:
        otp_attempts[phone_number] = (current_time, 1)

    return True


def send_otp_to_user_by_twilo(phone_number: str, code: str) -> bool:
    """
    Simple OTP sender for small projects
    Returns True if sent successfully, raises ValueError on error
    """
    try:
        # Validate phone number
        phone_number = validate_algerian_number(phone_number)

        # Check credentials
        if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_PHONE]):
            logger.error("Twilio credentials missing")
            raise ValueError("إعدادات Twilio غير مضبوطة")

        # Check rate limit
        if not check_rate_limit(phone_number):
            logger.warning(f"Rate limit exceeded for {phone_number}")
            raise ValueError("لقد تجاوزت الحد الأقصى. حاول بعد ساعة")

        # Create Twilio client
        client = Client(TWILIO_SID, TWILIO_TOKEN)

        # Send SMS
        message = client.messages.create(
            body=f"رمز التحقق من تصبيق أَسُولِي : {code}\nصالح لمدة ساعتين",
            from_=TWILIO_PHONE,
            to=phone_number
        )

        logger.info(f"✅ OTP sent to {phone_number}, SID: {message.sid}")
        return True

    except TwilioRestException as e:
        logger.error(f"Twilio error: {e.code} - {e.msg}")

        # Common errors
        if e.code == 21408:
            raise ValueError(
                "تأكد من تفعيل الجزائر في Twilio Geographic Permissions")
        elif e.code in [21211, 21614]:
            raise ValueError("رقم الهاتف غير صالح")
        elif e.code in [21610, 30005]:
            raise ValueError("الرقم غير موجود أو لا يمكن الوصول إليه")
        else:
            raise ValueError(f"خطأ في الإرسال: {e.msg}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise ValueError("فشل إرسال الرسالة")


def verify_otp(user_otp: str, stored_otp: str, expiration: datetime) -> bool:
    """Verify OTP code"""
    if datetime.utcnow() > expiration:
        return False
    return secrets.compare_digest(user_otp.strip(), stored_otp.strip())


# # server\utils\otp_utils.py
# import random
# from twilio.rest import Client
# import os

# from server.utils.phone_utils import validate_algerian_number

# TWILIO_SID = os.getenv("TWILIO_SID")
# TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
# TWILIO_PHONE = os.getenv("TWILIO_PHONE")


# def generate_otp_code(length: int = 6) -> str:
#     return ''.join([str(random.randint(0, 9)) for _ in range(length)])


# def send_otp_to_user_by_twilo(phone_number: str, code: str):
#     phone_number = validate_algerian_number(phone_number)
#     if not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_PHONE:
#         raise ValueError("إعدادات Twilio غير مضبوطة بشكل صحيح.")
#     client = Client(TWILIO_SID, TWILIO_TOKEN)
#     message = f"رمز التحقق الخاص بك هو {code}"
#     client.messages.create(
#         body=message,
#         from_=TWILIO_PHONE,
#         to=phone_number
#     )
