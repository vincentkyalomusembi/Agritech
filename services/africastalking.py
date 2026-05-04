import os
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

AT_API_KEY = os.getenv("AT_API_KEY")
AT_USERNAME = os.getenv("AT_USERNAME")


def _require_config():
    if not AT_API_KEY or not AT_USERNAME:
        raise RuntimeError("Africa's Talking credentials are not set in environment")


def send_sms(to: str, message: str, from_sender: Optional[str] = None) -> dict:
    """Send SMS via Africa's Talking REST API.

    Returns the parsed JSON response on success.
    """
    _require_config()
    url = "https://api.africastalking.com/version1/messaging"
    headers = {
        "apiKey": AT_API_KEY,
        "Accept": "application/json",
    }
    data = {
        "username": AT_USERNAME,
        "to": to,
        "message": message,
    }
    if from_sender:
        data["from"] = from_sender

    resp = requests.post(url, data=data, headers=headers, timeout=10)
    try:
        return resp.json()
    except Exception:
        return {"status_code": resp.status_code, "text": resp.text}


def notify_subscription(phone: str, plan: str = "weekly") -> dict:
    msg = f"Thank you for subscribing to Agritech ({plan}). You will receive tips and alerts."
    return send_sms(phone, msg)
