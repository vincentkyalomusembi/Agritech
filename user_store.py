"""Hardcoded demo users for the Agritech AI prototype."""

from typing import Any

USERS: list[dict[str, Any]] = [
    {
        "phone_number": "+254792246733",
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
    {
        "phone_number": "+254746064796",
        "name": "James Mwangi",
        "county": "Nakuru",
        "farm_type": "crop",
        "soil_type": "clay",
    },
    {
        "phone_number": "+254700000014",
        "name": "Jane Doe",
        "county": "Kakamega",
        "farm_type": "crop",
        "soil_type": "loamy",
    },
]

VETS: list[dict[str, Any]] = [
    {
        "phone_number": "+254700000004",
        "name": "Dr. Sarah Ochieng",
        "county": "Kisumu",
        "region": "Nyanza",
        "soil_type": "loamy",
    },
    {
        "phone_number": "+254700000005",
        "name": "Dr. John Kamau",
        "county": "Kiambu",
        "region": "Central",
        "soil_type": "sandy",
    },
    {
        "phone_number": "+254700000006",
        "name": "Dr. Grace Wanjiru",
        "county": "Mombasa",
        "region": "Coast",
        "soil_type": "sandy",
    },
    {
        "phone_number": "+254700000007",
        "name": "Dr. Michael Otieno",
        "county": "Siaya",
        "region": "Nyanza",
        "soil_type": "clay",
    },
    {
        "phone_number": "+254700000008",
        "name": "Dr. Faith Njeri",
        "county": "Nairobi",
        "region": "Nairobi",
        "soil_type": "loamy",
    },
]

AGRICULTURAL_OFFICERS: list[dict[str, Any]] = [
    {
        "phone_number": "+254700000009",
        "name": "David Mutiso",
        "county": "Machakos",
        "region": "Eastern",
        "soil_type": "sandy",
    },
    {
        "phone_number": "+254700000010",
        "name": "Rebecca Chebet",
        "county": "Uasin Gishu",
        "region": "Rift Valley",
        "soil_type": "loamy",
    },
    {
        "phone_number": "+254700000011",
        "name": "Samuel Kiplagat",
        "county": "Baringo",
        "region": "Rift Valley",
        "soil_type": "clay",
    },
    {
        "phone_number": "+254700000012",
        "name": "Lucy Wambui",
        "county": "Murang'a",
        "region": "Central",
        "soil_type": "sandy",
    },
    {
        "phone_number": "+254700000013",
        "name": "Peter Kariuki",
        "county": "Kirinyaga",
        "region": "Central",
        "soil_type": "loamy",
    },
]


def get_user_by_phone(phone_number: str):
    phone_number = (phone_number or "").strip()
    
    # Search in all user lists
    for user_list in [USERS, VETS, AGRICULTURAL_OFFICERS]:
        user = next((u for u in user_list if u["phone_number"] == phone_number), None)
        if user:
            return user
    return None


def list_users():
    return USERS.copy()
def list_vets():
    return VETS.copy()


def list_agricultural_officers():
    return AGRICULTURAL_OFFICERS.copy()


def list_all_users():
    """Returns all users (farmers, vets, and agricultural officers)"""
    return USERS + VETS + AGRICULTURAL_OFFICERS


def subscribe_user(phone_number: str, plan: str = "weekly"):
    phone_number = (phone_number or "").strip()
    user = get_user_by_phone(phone_number)
    if user:
        user["subscribed"] = True
        user["subscription_plan"] = plan
        return user
    # if not found, create a lightweight user record
    new = {
        "phone_number": phone_number,
        "name": None,
        "county": None,
        "farm_type": None,
        "soil_type": None,
        "subscribed": True,
        "subscription_plan": plan,
    }
    USERS.append(new)
    return new


def list_subscribers():
    return [u for u in USERS if u.get("subscribed")]


def update_user(phone_number: str, updates: dict):
    """Update user fields by phone number"""
    phone_number = (phone_number or "").strip()
    user = get_user_by_phone(phone_number)
    if user:
        user.update(updates)
        return user
    return None
