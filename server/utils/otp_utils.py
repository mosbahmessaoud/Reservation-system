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
TWILIO_MESSAGING_SERVICE_SID = os.getenv(
    "TWILIO_MESSAGING_SERVICE_SID", "VA118c8228ca9a7c4966ce9fa1a5ef34f7")

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
    Send YOUR custom OTP code using Twilio Messaging Service
    Uses your service SID: VA118c8228ca9a7c4966ce9fa1a5ef34f7
    """
    try:
        # Validate phone number
        phone_number = validate_algerian_number(phone_number)

        # Check credentials
        if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_MESSAGING_SERVICE_SID]):
            logger.error("Twilio credentials missing")
            raise ValueError("إعدادات Twilio غير مضبوطة")

        # Check rate limit
        if not check_rate_limit(phone_number):
            logger.warning(f"Rate limit exceeded for {phone_number}")
            raise ValueError("لقد تجاوزت الحد الأقصى. حاول بعد ساعة")

        # Create Twilio client
        client = Client(TWILIO_SID, TWILIO_TOKEN)

        # ✅ Send SMS with YOUR code using Messaging Service
        message = client.messages.create(
            messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
            body=f"رمز التحقق من أَسُولِي:{code}",
            to=phone_number
        )

        logger.info(f"✅ OTP {code} sent to {phone_number}, SID: {message.sid}")
        print(f"Message SID: {message.sid}")
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
        elif e.code == 21606:
            raise ValueError("رقم الهاتف في القائمة السوداء")
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
