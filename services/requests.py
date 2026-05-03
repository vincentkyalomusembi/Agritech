def create_visit_request(phone_number: str, county: str, issue: str):
    return {
        "status": "received",
        "phone_number": (phone_number or "").strip(),
        "county": (county or "").strip().title(),
        "issue": (issue or "").strip(),
    }