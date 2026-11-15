import re
import requests
from django.conf import settings


def format_indian_phone(phone: str) -> str:
    """Converts 10-digit or +91 numbers into clean 91XXXXXXXXXX format."""
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) == 10:
        return f"91{digits}"
    return digits


def send_rent_reminder(
    phone: str,
    student_name: str,
    amount: str | int,
    month_year: str,
    due_date: str,
) -> dict:
    """
    Sends the 'hostel_rent_reminder' WhatsApp template via Meta Cloud API.
    Parameter order:
      {{1}} -> student_name
      {{2}} -> amount
      {{3}} -> month_year
      {{4}} -> due_date
    """
    url = (
        f"https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": format_indian_phone(phone),
        "type": "template",
        "template": {
            "name": "hostel_rent_reminder",
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(student_name)},
                        {"type": "text", "text": str(amount)},
                        {"type": "text", "text": str(month_year)},
                        {"type": "text", "text": str(due_date)},
                    ],
                }
            ],
        },
    }

    response = requests.post(url, headers=headers, json=payload, timeout=15)
    return {
        "status_code": response.status_code,
        "ok": response.ok,
        "data": response.json(),
    }