import re


from fastapi import HTTPException


def validate_number_phone(phone: str) -> str:
    if not phone:  # catches None, empty string, etc.
        raise HTTPException(
            status_code=400,
            detail="Phone number is required."
        )

    phone = str(phone).strip()

    if len(phone) != 10 or not phone.isdigit():
        raise HTTPException(
            status_code=400,
            detail="Phone number must be exactly 10 digits."
        )

    if not (phone.startswith("05") or phone.startswith("06") or phone.startswith("07")):
        raise HTTPException(
            status_code=400,
            detail="Phone number must start with 05, 06, or 07."
        )

    return phone


def validate_number_phone_of_guardian(phone: str) -> str:
    if not phone:  # catches None, empty string, etc.
        raise HTTPException(
            status_code=400,
            detail="the guardian Phone number is required."
        )

    phone = str(phone).strip()

    if len(phone) != 10 or not phone.isdigit():
        raise HTTPException(
            status_code=400,
            detail="the guardian Phone number must be exactly 10 digits."
        )

    if not (phone.startswith("05") or phone.startswith("06") or phone.startswith("07")):
        raise HTTPException(
            status_code=400,
            detail="the guardian Phone number must start with 05, 06, or 07."
        )

    return phone

# def validate_number_phone_of_guardian(phone: str) -> str:

#     # Pattern: must start with 05, 06, or 07 and have exactly 10 digits
#     pattern = r"^0(5|6|7)[0-9]{8}$"
#     if not re.fullmatch(pattern, phone):
#         raise HTTPException(
#             status_code=400,
#             detail=" the phone number of guardian is not on valid format. make sur start with 06, 07, or 05 and has 10 digits ."
#         )

#     return phone


def validate_algerian_number(phone: str) -> str:
    # Remove any whitespace or special characters
    phone = ''.join(filter(str.isdigit, phone))

    # Check if the number starts with 0 (local format)
    if phone.startswith("0"):
        phone = "+213" + phone[1:]
    # Check if it's in the format +2130...
    elif phone.startswith("2130"):
        phone = "+213" + phone[4:]
    # Check if it's missing country code
    elif len(phone) == 9 and phone.startswith(('5', '6', '7')):
        phone = "+213" + phone
    # Check if it's in the format 00213...
    elif phone.startswith("00213"):
        phone = "+213" + phone[5:]

    # Validate the final format
    pattern = r"^\+213(5|6|7)[0-9]{8}$"
    if not re.fullmatch(pattern, phone):
        raise HTTPException(
            status_code=400,
            detail=" phone number is not on valid format. make sur start with 06, 07, or 05 and has 10 digits ."
        )

    return phone


def validate_algerian_number_for_guardian(phone: str) -> str:
    # Remove any whitespace or special characters
    phone = ''.join(filter(str.isdigit, phone))

    # Check if the number starts with 0 (local format)
    if phone.startswith("0"):
        phone = "+213" + phone[1:]
    # Check if it's in the format +2130...
    elif phone.startswith("2130"):
        phone = "+213" + phone[4:]
    # Check if it's missing country code
    elif len(phone) == 9 and phone.startswith(('5', '6', '7')):
        phone = "+213" + phone
    # Check if it's in the format 00213...
    elif phone.startswith("00213"):
        phone = "+213" + phone[5:]

    # Validate the final format
    pattern = r"^\+213(5|6|7)[0-9]{8}$"
    if not re.fullmatch(pattern, phone):
        raise HTTPException(
            status_code=400,
            detail=" phone number of the guardian is not on valid format. make sur start with 06, 07, or 05 and has 10 digits ."
        )

    return phone
# def validate_algerian_number_for_guardian(phone: str) -> str:
#     original_input = phone.strip()

#     # Case 1: Starts with +213
#     if original_input.startswith("+213"):
#         if not re.fullmatch(r"^\+213[0-9]{9}$", original_input):
#             raise HTTPException(
#                 status_code=400,
#                 detail="When using international format, the number must contain exactly 13 characters starting with +213."
#             )
#         if not original_input[4] in {"5", "6", "7"}:
#             raise HTTPException(
#                 status_code=400,
#                 detail="When using international format, the number must start with +2135, +2136, or +2137."
#             )
#         return original_input

#     # Case 2: Starts with 0 (local format)
#     if original_input.startswith("0"):
#         if len(original_input) != 10:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Local phone numbers must contain exactly 10 digits."
#             )
#         if not original_input[1] in {"5", "6", "7"}:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Local phone numbers must start with 05, 06, or 07."
#             )
#         return "+213" + original_input[1:]  # Convert to international format

#     # Case 3: Anything else → invalid format
#     raise HTTPException(
#         status_code=400,
#         detail="Phone number format is not recognized. Use either local (starts with 0) or international (+213) format."
#     )
