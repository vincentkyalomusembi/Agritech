"""Hardcoded demo users for the Agritech AI prototype."""

USERS = [
    {
        "phone_number": "+254700000001",
        "name": "Vin Demo",
        "county": "Makueni",
        "farm_type": "crop",
        "soil_type": "sandy",
    },
    {
        "phone_number": "+254700000002",
        "name": "Amina Demo",
        "county": "Nyeri",
        "farm_type": "livestock",
        "soil_type": "loamy",
    },
]


def get_user_by_phone(phone_number: str):
    phone_number = (phone_number or "").strip()
    return next((user for user in USERS if user["phone_number"] == phone_number), None)


def list_users():
    return USERS.copy()