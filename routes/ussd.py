"""
routes/ussd.py
Africa's Talking USSD callback — full 9-option menu.

Navigation model
----------------
Stateless text.split("*") — Africa's Talking always sends the full session
path in `text`, so a server restart never drops a user mid-flow.

Session store (db/sessions.py)
--------------------------------
Server-side state is only used for persistent profile data that can't live
in the menu path: name, county, farm_type, onboarded flag.
Sessions are SQLite-backed now, Supabase-swappable in Phase 1.

Menu structure
--------------
  Main menu:
    1. Crop Recommendation
    2. Livestock Recommendation
    3. Weather Alerts          (subscribers only)
    4. Disease Alerts          (subscribers only)
    5. Market Prices
    6. Request Expert Visit
    7. Advisory Tips
    8. My Profile
    9. Subscribe

CON / END rules
---------------
  CON = session continues, user can press more keys
  END = session ends, user reads final message
  182-char hard limit on CON body (Africa's Talking truncates silently)
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from db.sessions import get_session, set_session
from db.users import list_vets, list_agri_officers
from db.subscriptions import get_subscription
from models.recommender import build_recommendation, list_counties
from services.weather import get_weather
from services.alerts import build_weather_alert, build_disease_alert
from services.market import get_market_prices, format_price_for_ussd, USSD_COMMODITY_MAP
from services.advisory import get_advisory_tips

router = APIRouter()

MAX_CON_LEN = 182


# ── Response helpers ──────────────────────────────────────────────────────────

def con(text: str) -> PlainTextResponse:
    return PlainTextResponse(f"CON {text[:MAX_CON_LEN]}")

def end(text: str) -> PlainTextResponse:
    return PlainTextResponse(f"END {text}")


# ── Subscription check ────────────────────────────────────────────────────────

def _is_subscribed(phone_number: str) -> bool:
    """Returns True if the phone number has an active subscription."""
    try:
        sub = get_subscription(phone_number)
        return bool(sub and sub.get("status") == "active")
    except Exception:
        return False


# ── Onboarding ────────────────────────────────────────────────────────────────

def _needs_onboarding(session: dict) -> bool:
    return not session.get("onboarded", False)


def _handle_onboarding(steps: list, phone_number: str, session: dict) -> PlainTextResponse:
    """
    Linear 3-step onboarding before the main menu is shown.
    Writes profile to session AND to users table (best-effort).
    """
    counties = list_counties()

    if len(steps) == 0:
        return con(
            "Welcome to Agritech AI\n"
            "Quick setup (3 steps).\n"
            "Enter your name:"
        )

    if len(steps) == 1:
        set_session(phone_number, {"name": steps[0]})
        county_list = "\n".join(f"{i}. {c}" for i, c in enumerate(counties, 1))
        return con(f"Select your county:\n{county_list}")

    if len(steps) == 2:
        try:
            idx = int(steps[1]) - 1
            if not (0 <= idx < len(counties)):
                county_list = "\n".join(f"{i}. {c}" for i, c in enumerate(counties, 1))
                return con(f"Invalid. Select county:\n{county_list}")
            set_session(phone_number, {"county": counties[idx]})
        except ValueError:
            return con("Enter a number for your county.")
        return con("Select farm type:\n1. Crop\n2. Livestock")

    if len(steps) >= 3:
        farm_map = {"1": "crop", "2": "livestock"}
        farm_type = farm_map.get(steps[2])
        if not farm_type:
            return con("Enter 1 for Crop or 2 for Livestock:")
        set_session(phone_number, {"farm_type": farm_type, "onboarded": True})
        session = get_session(phone_number)

        try:
            from db.users import upsert_user
            upsert_user(
                phone=phone_number,
                data={
                    "name":      session.get("name"),
                    "county":    session.get("county"),
                    "farm_type": farm_type,
                    "onboarded": True,
                },
            )
        except Exception as exc:
            print(f"[ussd] upsert_user failed (non-fatal): {exc}")

        name = session.get("name", "Farmer")
        return con(_main_menu(name))

    return con("Welcome to Agritech AI. Enter your name:")


# ── Screen builders ───────────────────────────────────────────────────────────

def _main_menu(name: str = "Farmer") -> str:
    return (
        f"Hi {name}\n"
        "1. Crop Recommendation\n"
        "2. Livestock Recommendation\n"
        "3. Weather Alerts\n"
        "4. Disease Alerts\n"
        "5. Market Prices\n"
        "6. Expert Visit\n"
        "7. Advisory Tips\n"
        "8. My Profile\n"
        "9. Subscribe"
    )


def _county_menu() -> str:
    counties = list_counties()
    lines = ["Select county:"]
    lines += [f"{i}. {c}" for i, c in enumerate(counties, 1)]
    return "\n".join(lines)


def _farm_type_menu(county: str) -> str:
    return f"County: {county}\n1. Crop\n2. Livestock"


def _recommendation_screen(county: str, farm_type: str) -> str:
    weather = get_weather(county)
    result = build_recommendation(county, farm_type, weather)

    if not result:
        return f"No data for {county}. Contact support."

    src = "live" if (weather or {}).get("source") == "openweather" else "est."
    lines = [
        f"{result['county']} | {farm_type.title()}",
        f"Soil: {result['soil_type']}",
        f"Rainfall avg: {result['avg_rainfall']}mm",
    ]
    if weather and weather.get("temp") is not None:
        lines.append(f"Temp: {weather['temp']}°C ({src})")
    lines.append(f"\nRecommended: {result['recommendation'].upper()}")
    for note in result["weather_notes"]:
        lines.append(f"Note: {note}")
    return "\n".join(lines)


def _market_menu() -> str:
    lines = ["Select commodity:"]
    labels = {
        "1": "Maize",   "2": "Beans",  "3": "Green Grams",
        "4": "Sorghum", "5": "Wheat",  "6": "Potato",
        "7": "Goat",    "8": "Chicken","9": "Dairy",
        "10": "Fish",
    }
    lines += [f"{k}. {v}" for k, v in labels.items()]
    return "\n".join(lines)


def _expert_screen(expert_type: str, county: str | None) -> str:
    """Returns formatted expert list for vets or agri officers."""
    if expert_type == "1":
        experts = list_vets(county=county, limit=3)
        title = "Veterinary Officers"
    else:
        experts = list_agri_officers(county=county, limit=3)
        title = "Agricultural Officers"

    if not experts:
        return f"No {title.lower()} found. Try 0800 720 410 (Ministry helpline)."

    lines = [f"{title}:"]
    for e in experts:
        lines.append(f"• {e['name']} — {e['county']}")
    lines.append("Call to book a visit.")
    return "\n".join(lines)


def _profile_screen(session: dict) -> str:
    return (
        f"My Profile\n"
        f"Name: {session.get('name', 'N/A')}\n"
        f"County: {session.get('county', 'N/A')}\n"
        f"Farm type: {session.get('farm_type', 'N/A')}\n"
        "1. Edit county\n"
        "2. Edit farm type"
    )


def _subscribe_screen(phone_number: str) -> str:
    """Activates a free weekly subscription and returns confirmation text."""
    try:
        from db.subscriptions import create_subscription
        create_subscription(phone_number, plan="weekly")
    except Exception as exc:
        print(f"[ussd] subscribe failed (non-fatal): {exc}")

    return (
        f"Subscribed!\n"
        f"Phone: {phone_number}\n"
        "You will now receive weekly weather and disease alerts.\n"
        "Dial again anytime for full access."
    )


# ── Saved-county helper ───────────────────────────────────────────────────────

def _resolve_county(steps: list, step_index: int, session: dict, phone_number: str, allow_change: bool = True):
    """
    Resolves county from either session (saved) or user input (typed number).
    Returns (county_str | None, needs_more_input: bool, response: PlainTextResponse | None)
    If needs_more_input is True, response is the CON to send back.
    """
    saved = session.get("county")
    if saved and step_index >= len(steps):
        return saved, False, None
    if step_index < len(steps):
        counties = list_counties()
        try:
            idx = int(steps[step_index]) - 1
            if 0 <= idx < len(counties):
                county = counties[idx]
                set_session(phone_number, {"county": county})
                return county, False, None
        except ValueError:
            pass
        return None, False, end("Invalid county number. Try again.")
    return None, True, con(_county_menu())


# ── USSD callback ─────────────────────────────────────────────────────────────

@router.post("/ussd", response_class=PlainTextResponse)
async def ussd_callback(request: Request):
    form = await request.form()
    phone_number: str = form.get("phoneNumber", "")
    text: str = form.get("text", "")

    steps = [s for s in text.split("*") if s != ""]
    session = get_session(phone_number)

    # ── Onboarding gate ───────────────────────────────────────────────────────
    if _needs_onboarding(session):
        return _handle_onboarding(steps, phone_number, session)

    name = session.get("name", "Farmer")
    saved_county = session.get("county")
    saved_farm = session.get("farm_type", "crop")

    # ── Level 0: main menu ────────────────────────────────────────────────────
    if not steps:
        return con(_main_menu(name))

    option = steps[0]

    # ──────────────────────────────────────────────────────────────────────────
    # OPTION 1 — Crop Recommendation
    # ──────────────────────────────────────────────────────────────────────────
    if option == "1":
        if len(steps) == 1:
            if saved_county:
                return con(f"County: {saved_county}\n1. Confirm\n2. Change county")
            return con(_county_menu())

        if len(steps) == 2:
            if saved_county:
                if steps[1] == "1":
                    return end(_recommendation_screen(saved_county, "crop"))
                elif steps[1] == "2":
                    return con(_county_menu())
                return end("Invalid choice.")
            else:
                counties = list_counties()
                try:
                    idx = int(steps[1]) - 1
                    if not (0 <= idx < len(counties)):
                        return con(f"Invalid.\n{_county_menu()}")
                    county = counties[idx]
                    set_session(phone_number, {"county": county})
                    return end(_recommendation_screen(county, "crop"))
                except ValueError:
                    return con(f"Enter a number.\n{_county_menu()}")

        if len(steps) == 3 and saved_county and steps[1] == "2":
            # Changed county
            counties = list_counties()
            try:
                idx = int(steps[2]) - 1
                if not (0 <= idx < len(counties)):
                    return con(f"Invalid.\n{_county_menu()}")
                county = counties[idx]
                set_session(phone_number, {"county": county})
                return end(_recommendation_screen(county, "crop"))
            except ValueError:
                return con(f"Enter a number.\n{_county_menu()}")

    # ──────────────────────────────────────────────────────────────────────────
    # OPTION 2 — Livestock Recommendation
    # ──────────────────────────────────────────────────────────────────────────
    elif option == "2":
        if len(steps) == 1:
            if saved_county:
                return con(f"County: {saved_county}\n1. Confirm\n2. Change county")
            return con(_county_menu())

        if len(steps) == 2:
            if saved_county:
                if steps[1] == "1":
                    return end(_recommendation_screen(saved_county, "livestock"))
                elif steps[1] == "2":
                    return con(_county_menu())
                return end("Invalid choice.")
            else:
                counties = list_counties()
                try:
                    idx = int(steps[1]) - 1
                    if not (0 <= idx < len(counties)):
                        return con(f"Invalid.\n{_county_menu()}")
                    county = counties[idx]
                    set_session(phone_number, {"county": county})
                    return end(_recommendation_screen(county, "livestock"))
                except ValueError:
                    return con(f"Enter a number.\n{_county_menu()}")

        if len(steps) == 3 and saved_county and steps[1] == "2":
            counties = list_counties()
            try:
                idx = int(steps[2]) - 1
                if not (0 <= idx < len(counties)):
                    return con(f"Invalid.\n{_county_menu()}")
                county = counties[idx]
                set_session(phone_number, {"county": county})
                return end(_recommendation_screen(county, "livestock"))
            except ValueError:
                return con(f"Enter a number.\n{_county_menu()}")

    # ──────────────────────────────────────────────────────────────────────────
    # OPTION 3 — Weather Alerts (subscribers only)
    # ──────────────────────────────────────────────────────────────────────────
    elif option == "3":
        if not _is_subscribed(phone_number):
            return end(
                "Weather alerts are for subscribers.\n"
                "Dial back and select option 9 to subscribe."
            )
        county = saved_county
        if not county:
            if len(steps) == 1:
                return con("Enter county number for alerts:\n" + _county_menu())
            counties = list_counties()
            try:
                idx = int(steps[1]) - 1
                county = counties[idx] if 0 <= idx < len(counties) else None
            except (ValueError, IndexError):
                county = None
            if not county:
                return end("Invalid county. Try again.")
        return end(build_weather_alert(county, subscribed=True))

    # ──────────────────────────────────────────────────────────────────────────
    # OPTION 4 — Disease Alerts (subscribers only)
    # ──────────────────────────────────────────────────────────────────────────
    elif option == "4":
        if not _is_subscribed(phone_number):
            return end(
                "Disease alerts are for subscribers.\n"
                "Dial back and select option 9 to subscribe."
            )
        county = saved_county
        if not county:
            if len(steps) == 1:
                return con("Enter county number for alerts:\n" + _county_menu())
            counties = list_counties()
            try:
                idx = int(steps[1]) - 1
                county = counties[idx] if 0 <= idx < len(counties) else None
            except (ValueError, IndexError):
                county = None
            if not county:
                return end("Invalid county. Try again.")
        return end(build_disease_alert(county, subscribed=True))

    # ──────────────────────────────────────────────────────────────────────────
    # OPTION 5 — Market Prices
    # ──────────────────────────────────────────────────────────────────────────
    elif option == "5":
        if len(steps) == 1:
            return con(_market_menu())

        commodity = USSD_COMMODITY_MAP.get(steps[1])
        if not commodity:
            return con(f"Invalid.\n{_market_menu()}")

        price_data = get_market_prices(commodity, county=saved_county)
        return end(format_price_for_ussd(commodity, price_data))

    # ──────────────────────────────────────────────────────────────────────────
    # OPTION 6 — Request Expert Visit
    # ──────────────────────────────────────────────────────────────────────────
    elif option == "6":
        if len(steps) == 1:
            return con("Select expert type:\n1. Veterinary Officer\n2. Agricultural Officer")

        expert_type = steps[1]
        if expert_type not in ("1", "2"):
            return con("Enter 1 (Vet) or 2 (Agri Officer):")

        return end(_expert_screen(expert_type, county=saved_county))

    # ──────────────────────────────────────────────────────────────────────────
    # OPTION 7 — Advisory Tips
    # ──────────────────────────────────────────────────────────────────────────
    elif option == "7":
        tips = get_advisory_tips(
            farm_type=saved_farm,
            county=saved_county,
        )
        return end(tips)

    # ──────────────────────────────────────────────────────────────────────────
    # OPTION 8 — My Profile
    # ──────────────────────────────────────────────────────────────────────────
    elif option == "8":
        if len(steps) == 1:
            return con(_profile_screen(session))

        if len(steps) == 2:
            if steps[1] == "1":
                return con(_county_menu())
            elif steps[1] == "2":
                return con("Farm type:\n1. Crop\n2. Livestock")
            return con(f"Invalid.\n{_profile_screen(session)}")

        if len(steps) == 3:
            if steps[1] == "1":
                counties = list_counties()
                try:
                    idx = int(steps[2]) - 1
                    if not (0 <= idx < len(counties)):
                        return con(f"Invalid.\n{_county_menu()}")
                    new_county = counties[idx]
                    set_session(phone_number, {"county": new_county})
                    return end(f"County updated to {new_county}.")
                except ValueError:
                    return con(f"Enter a number.\n{_county_menu()}")

            elif steps[1] == "2":
                farm_map = {"1": "crop", "2": "livestock"}
                farm_type = farm_map.get(steps[2])
                if not farm_type:
                    return con("Enter 1 (Crop) or 2 (Livestock):")
                set_session(phone_number, {"farm_type": farm_type})
                return end(f"Farm type updated to {farm_type}.")

    # ──────────────────────────────────────────────────────────────────────────
    # OPTION 9 — Subscribe
    # ──────────────────────────────────────────────────────────────────────────
    elif option == "9":
        if _is_subscribed(phone_number):
            return end(
                "You are already subscribed.\n"
                "You receive weekly weather and disease alerts."
            )
        if len(steps) == 1:
            return con(
                "Subscribe to Agritech AI\n"
                "Weekly weather + disease alerts\n"
                "1. Subscribe (Free beta)\n"
                "2. Cancel"
            )
        if steps[1] == "1":
            return end(_subscribe_screen(phone_number))
        return end("Subscription cancelled. Dial again anytime.")

    return con(_main_menu(name))