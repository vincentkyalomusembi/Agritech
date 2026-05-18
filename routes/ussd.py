"""
routes/ussd.py
Africa's Talking USSD callback — full 9-option menu.

Menu map
--------
  0 (new user)           onboarding: name → county → farm_type
  Main menu
    1. Get Recommendation
    2. My Profile         (edit county / farm_type)
    3. Weather Alerts
    4. Disease Alerts
    5. Market Prices
    6. Book Expert Visit
    7. Advisory Tips
    8. My Subscription
    9. About

Subscription gate
-----------------
  Options 3–8 are gated: free-plan users see a prompt to subscribe.
  Option 1, 2, 9 are always available.

Data persistence
----------------
  Every set_session() call now goes through the read→merge→write fix in
  db/sessions.py so partial field updates never wipe other fields.

  At the end of onboarding, upsert_user() is called to persist the farmer
  profile to Supabase (gracefully skipped if Supabase isn't configured yet).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from db.sessions import delete_session, get_session, set_session
from models.recommender import build_recommendation, list_counties
from services.weather import get_weather

log = logging.getLogger(__name__)

router = APIRouter()

MAX_CON_LEN = 182    # Africa's Talking CON body hard limit


# ── Response helpers ──────────────────────────────────────────────────────────

def con(text: str) -> PlainTextResponse:
    """Continue — user stays in session."""
    body = text[:MAX_CON_LEN]
    return PlainTextResponse(f"CON {body}")


def end(text: str) -> PlainTextResponse:
    """End — session closes after user reads."""
    return PlainTextResponse(f"END {text}")


# ── Subscription helpers ──────────────────────────────────────────────────────

def _is_subscribed(session: dict) -> bool:
    """
    Returns True if the user has an active paid subscription.
    We store subscription_plan in the session as a fast-path check.
    Falls back to Supabase if needed (graceful — never blocks).
    """
    # Fast-path: session already has the plan cached
    plan = session.get("subscription_plan", "free")
    if plan in ("basic", "pro"):
        return True

    # Slow-path: check Supabase subscriptions table
    phone = session.get("phone")
    if not phone:
        return False
    try:
        from db.users import get_user
        from db.subscriptions import is_active
        user = get_user(phone)
        if user and user.get("id"):
            return is_active(user["id"])
    except Exception as exc:
        log.debug("[ussd] subscription check failed: %s", exc)
    return False


def _subscription_gate(session: dict) -> PlainTextResponse | None:
    """Returns a CON prompt if not subscribed, None if OK to proceed."""
    if _is_subscribed(session):
        return None
    return con(
        "Premium feature 🔒\n"
        "Subscribe to unlock:\n"
        "1. Subscribe (KES 50/month)\n"
        "0. Back to menu"
    )


# ── Supabase persistence (fire-and-forget) ────────────────────────────────────

def _persist_user(phone: str, session: dict) -> None:
    """
    Calls upsert_user() to write the session profile to Supabase.
    Swallows all errors — never blocks the USSD response.
    """
    try:
        from db.users import upsert_user
        upsert_user(phone, {
            "name":      session.get("name"),
            "county":    session.get("county"),
            "farm_type": session.get("farm_type"),
            "onboarded": True,
        })
    except Exception as exc:
        log.warning("[ussd] upsert_user(%s) failed (Supabase not configured?): %s", phone, exc)


# ── Onboarding ────────────────────────────────────────────────────────────────

def _needs_onboarding(session: dict) -> bool:
    return not session.get("onboarded", False)


def _handle_onboarding(steps: list[str], phone_number: str, session: dict) -> PlainTextResponse:
    """
    Linear 3-step onboarding: name → county → farm_type.

    Steps breakdown:
      0 steps  → ask name
      1 step   → got name, ask county
      2 steps  → got county, ask farm type
      3+ steps → complete, save to session + Supabase, show main menu
    """
    counties = list_counties()

    if len(steps) == 0:
        return con(
            "Welcome to Agritech AI 🌾\n"
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
                return con(f"Invalid number. Select county:\n{county_list}")
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

        # Persist to Supabase (non-blocking)
        _persist_user(phone_number, session)

        name = session.get("name", "Farmer")
        return con(_main_menu(name))

    return con("Welcome to Agritech AI. Enter your name:")


# ── Menu screens ──────────────────────────────────────────────────────────────

def _main_menu(name: str = "Farmer") -> str:
    return (
        f"Hi {name} 🌾\n"
        "1. Get Recommendation\n"
        "2. My Profile\n"
        "3. Weather Alerts\n"
        "4. Disease Alerts\n"
        "5. Market Prices\n"
        "6. Book Expert Visit\n"
        "7. Advisory Tips\n"
        "8. My Subscription\n"
        "9. About"
    )


def _county_menu() -> str:
    counties = list_counties()
    lines = ["Select your county:"]
    lines += [f"{i}. {c}" for i, c in enumerate(counties, 1)]
    return "\n".join(lines)


def _farm_type_menu(county: str) -> str:
    return (
        f"County: {county}\n"
        "Farm type:\n"
        "1. Crop\n"
        "2. Livestock"
    )


def _profile_screen(session: dict) -> str:
    return (
        "My Profile\n"
        f"Name: {session.get('name', 'N/A')}\n"
        f"County: {session.get('county', 'N/A')}\n"
        f"Farm type: {session.get('farm_type', 'N/A')}\n"
        "1. Edit county\n"
        "2. Edit farm type"
    )


def _recommendation_screen(county: str, farm_type: str) -> str:
    weather = get_weather(county)
    result  = build_recommendation(county, farm_type, weather)

    if not result:
        return f"No data found for {county}. Try again or contact support."

    src       = "live" if (weather or {}).get("source") == "openweather" else "est."
    temp_line = f"🌡 Temp: {weather['temp']}°C ({src})" if weather else ""

    lines = [
        f"📍 {result['county']} | {result['farm_type'].title()}",
        f"🌱 Soil: {result['soil_type']}",
        f"🌧 Rainfall: {result['avg_rainfall']}mm avg",
    ]
    if temp_line:
        lines.append(temp_line)
    lines.append(f"\n✅ Recommended: {result['recommendation'].upper()}")
    for note in result["weather_notes"]:
        lines.append(f"⚠ {note}")

    return "\n".join(lines)


# ── Advisory helpers ──────────────────────────────────────────────────────────

def _weather_alerts(county: str) -> str:
    weather = get_weather(county)
    if not weather:
        return f"No weather data available for {county}.\nDial again later."

    src  = "Live" if weather.get("source") == "openweather" else "Estimated"
    temp = weather.get("temp", "N/A")
    hum  = weather.get("humidity", "N/A")
    cond = weather.get("condition", "N/A")
    spd  = weather.get("wind_speed", "N/A")

    lines = [
        f"🌦 Weather — {county} ({src})",
        f"🌡 {temp}°C | 💧 {hum}% humidity",
        f"☁ {cond}",
        f"💨 Wind: {spd} m/s",
    ]

    # Actionable alerts
    if isinstance(temp, (int, float)):
        if temp > 35:
            lines.append("⚠ Extreme heat — irrigate crops.")
        elif temp < 12:
            lines.append("⚠ Cold snap — protect seedlings.")

    if isinstance(hum, (int, float)) and hum > 85:
        lines.append("⚠ High humidity — watch for fungal diseases.")

    return "\n".join(lines)


def _disease_alerts(county: str, farm_type: str) -> str:
    # Static rule-based disease calendar — no external service required.
    # This mirrors the advisory logic from the main branch.
    weather = get_weather(county)
    hum     = (weather or {}).get("humidity", 60)
    temp    = (weather or {}).get("temp", 22)

    alerts = []

    if farm_type == "crop":
        if hum > 75:
            alerts.append("🍄 High fungal risk: apply fungicide on maize/beans.")
        if temp > 30:
            alerts.append("🐛 Armyworm risk elevated. Scout fields daily.")
        if not alerts:
            alerts.append("✅ No major crop disease alerts for your area.")
    else:
        if hum > 80:
            alerts.append("🦠 Foot-and-mouth risk elevated. Check livestock hooves.")
        if temp > 32:
            alerts.append("🌡 Heat stress: ensure animals have shade & water.")
        if not alerts:
            alerts.append("✅ No major livestock disease alerts for your area.")

    lines = [f"🔬 Disease Alerts — {county}"] + alerts
    return "\n".join(lines)


def _market_prices(county: str, farm_type: str) -> str:
    """
    Returns indicative wholesale prices for the recommended crop/livestock
    product in the farmer's county.  Uses static county profiles for now;
    will pull live data once the market service is wired up.
    """
    from models.recommender import get_county_data

    profile = get_county_data(county, farm_type)
    rec     = (profile or {}).get("csv_recommendation", "produce")

    # Static price guide (KES/kg or per unit) — based on KACE averages.
    PRICE_GUIDE: dict[str, str] = {
        "maize":        "KES 35–45 /kg",
        "beans":        "KES 100–130 /kg",
        "potato":       "KES 30–50 /kg",
        "wheat":        "KES 40–55 /kg",
        "rice":         "KES 80–100 /kg",
        "sorghum":      "KES 25–35 /kg",
        "green_grams":  "KES 90–120 /kg",
        "cassava":      "KES 20–30 /kg",
        "tea":          "KES 18–25 /kg (green leaf)",
        "coconut":      "KES 30–50 /nut",
        "dairy_cow":    "KES 35–45 /litre (milk)",
        "beef_cattle":  "KES 350–500 /kg (live wt.)",
        "goat":         "KES 7,000–12,000 /head",
        "chicken":      "KES 500–800 /bird",
        "camel":        "KES 50–80 /litre (milk)",
        "fish_farming": "KES 250–400 /kg (tilapia)",
    }

    price = PRICE_GUIDE.get(rec, "Price data not available")
    return (
        f"📊 Market Prices — {county}\n"
        f"🌾 {rec.replace('_', ' ').title()}\n"
        f"💰 {price}\n"
        "Source: KACE indicative averages.\n"
        "Prices vary by season & market."
    )


def _advisory_tips(county: str, farm_type: str) -> str:
    from models.recommender import get_county_data

    profile = get_county_data(county, farm_type)
    rec     = (profile or {}).get("csv_recommendation", "your crop")
    rain    = (profile or {}).get("avg_rainfall", 800)

    tips: list[str] = []

    if farm_type == "crop":
        tips.append(f"🌱 Best for {county}: {rec.replace('_', ' ').title()}")
        if rain < 400:
            tips.append("💧 Use drought-tolerant varieties & mulching.")
        elif rain > 1200:
            tips.append("🌧 Ensure good drainage; use raised beds if needed.")
        tips.append("🌿 Apply DAP at planting; CAN top-dressing at knee height.")
    else:
        tips.append(f"🐄 Best for {county}: {rec.replace('_', ' ').title()}")
        tips.append("💊 Deworm every 3 months; vaccinate before rainy season.")
        tips.append("🌾 Supplement feed during dry season.")

    return "\n".join([f"📋 Advisory — {county}"] + tips)


def _subscription_info(session: dict, phone_number: str) -> str:
    subscribed = _is_subscribed(session)
    plan       = session.get("subscription_plan", "Free")
    if subscribed:
        return (
            f"📋 Subscription: {plan.title()} plan\n"
            "✅ All features unlocked.\n"
            "To cancel, contact support:\n"
            "support@agritech.ai"
        )
    return (
        "📋 Subscription: Free plan\n"
        "Upgrade to unlock:\n"
        "• Weather Alerts\n"
        "• Disease Alerts\n"
        "• Market Prices\n"
        "• Expert Visits\n"
        "• Advisory Tips\n"
        "KES 50/month via M-PESA.\n"
        "Pay to: 123456 (AgriTech)"
    )


# ── USSD callback ─────────────────────────────────────────────────────────────

@router.post("/ussd", response_class=PlainTextResponse)
async def ussd_callback(request: Request):
    form         = await request.form()
    phone_number = str(form.get("phoneNumber", ""))
    text         = str(form.get("text", ""))

    steps   = [s for s in text.split("*") if s != ""]
    session = get_session(phone_number)

    # Cache the phone in session for subscription checks
    if phone_number and not session.get("phone"):
        set_session(phone_number, {"phone": phone_number})
        session = get_session(phone_number)

    # ── Onboarding gate ───────────────────────────────────────────────────────
    if _needs_onboarding(session):
        return _handle_onboarding(steps, phone_number, session)

    name        = session.get("name", "Farmer")
    county      = session.get("county", "")
    farm_type   = session.get("farm_type", "crop")

    # ── Level 0: main menu ────────────────────────────────────────────────────
    if len(steps) == 0:
        return con(_main_menu(name))

    option = steps[0]

    # ────────────────────────────────────────────────────────────────────────
    # Option 1: Recommendation
    # ────────────────────────────────────────────────────────────────────────
    if option == "1":
        saved_county = session.get("county")

        if len(steps) == 1:
            if saved_county:
                return con(
                    f"County: {saved_county}\n"
                    "Farm type:\n"
                    "1. Crop\n"
                    "2. Livestock\n"
                    "3. Change county"
                )
            return con(_county_menu())

        if len(steps) == 2:
            if saved_county:
                if steps[1] == "3":
                    return con(_county_menu())
                farm_map  = {"1": "crop", "2": "livestock"}
                farm_type = farm_map.get(steps[1])
                if not farm_type:
                    return con(f"Enter 1 (Crop) or 2 (Livestock):\n(County: {saved_county})")
                return end(_recommendation_screen(saved_county, farm_type))
            else:
                counties = list_counties()
                try:
                    idx = int(steps[1]) - 1
                    if not (0 <= idx < len(counties)):
                        return con(f"Invalid number.\n{_county_menu()}")
                    selected = counties[idx]
                    set_session(phone_number, {"county": selected})
                    return con(_farm_type_menu(selected))
                except ValueError:
                    return con(f"Enter a number.\n{_county_menu()}")

        if len(steps) == 3:
            if saved_county and steps[1] == "3":
                counties = list_counties()
                try:
                    idx = int(steps[2]) - 1
                    if not (0 <= idx < len(counties)):
                        return con(f"Invalid.\n{_county_menu()}")
                    new_county = counties[idx]
                    set_session(phone_number, {"county": new_county})
                    return con(_farm_type_menu(new_county))
                except ValueError:
                    return con(f"Enter a number.\n{_county_menu()}")
            else:
                counties = list_counties()
                try:
                    idx = int(steps[1]) - 1
                    if not (0 <= idx < len(counties)):
                        return con(f"Invalid county.\n{_county_menu()}")
                    selected  = counties[idx]
                    farm_map  = {"1": "crop", "2": "livestock"}
                    farm_type = farm_map.get(steps[2])
                    if not farm_type:
                        return con(f"Enter 1 or 2.\n{_farm_type_menu(selected)}")
                    return end(_recommendation_screen(selected, farm_type))
                except ValueError:
                    return con("Invalid input. Start again.")

        if len(steps) == 4:
            counties = list_counties()
            try:
                idx = int(steps[2]) - 1
                if not (0 <= idx < len(counties)):
                    return con(f"Invalid county.\n{_county_menu()}")
                selected  = counties[idx]
                farm_map  = {"1": "crop", "2": "livestock"}
                farm_type = farm_map.get(steps[3])
                if not farm_type:
                    return con(f"Enter 1 or 2.\n{_farm_type_menu(selected)}")
                return end(_recommendation_screen(selected, farm_type))
            except (ValueError, IndexError):
                return con("Invalid input. Start again.")

    # ────────────────────────────────────────────────────────────────────────
    # Option 2: Profile
    # ────────────────────────────────────────────────────────────────────────
    elif option == "2":
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
                    set_session(phone_number, {"county": counties[idx]})
                    _persist_user(phone_number, get_session(phone_number))
                    return end(f"County updated to {counties[idx]}.")
                except ValueError:
                    return con(f"Enter a number.\n{_county_menu()}")
            elif steps[1] == "2":
                farm_map  = {"1": "crop", "2": "livestock"}
                farm_type = farm_map.get(steps[2])
                if not farm_type:
                    return con("Enter 1 (Crop) or 2 (Livestock):")
                set_session(phone_number, {"farm_type": farm_type})
                _persist_user(phone_number, get_session(phone_number))
                return end(f"Farm type updated to {farm_type}.")

    # ────────────────────────────────────────────────────────────────────────
    # Option 3: Weather Alerts (premium)
    # ────────────────────────────────────────────────────────────────────────
    elif option == "3":
        gate = _subscription_gate(session)
        if gate:
            if len(steps) == 2 and steps[1] == "0":
                return con(_main_menu(name))
            return gate
        if not county:
            return con(f"Set your county first.\n{_county_menu()}")
        return end(_weather_alerts(county))

    # ────────────────────────────────────────────────────────────────────────
    # Option 4: Disease Alerts (premium)
    # ────────────────────────────────────────────────────────────────────────
    elif option == "4":
        gate = _subscription_gate(session)
        if gate:
            if len(steps) == 2 and steps[1] == "0":
                return con(_main_menu(name))
            return gate
        if not county:
            return con(f"Set your county first.\n{_county_menu()}")
        return end(_disease_alerts(county, farm_type))

    # ────────────────────────────────────────────────────────────────────────
    # Option 5: Market Prices (premium)
    # ────────────────────────────────────────────────────────────────────────
    elif option == "5":
        gate = _subscription_gate(session)
        if gate:
            if len(steps) == 2 and steps[1] == "0":
                return con(_main_menu(name))
            return gate
        if not county:
            return con(f"Set your county first.\n{_county_menu()}")
        return end(_market_prices(county, farm_type))

    # ────────────────────────────────────────────────────────────────────────
    # Option 6: Book Expert Visit (premium)
    # ────────────────────────────────────────────────────────────────────────
    elif option == "6":
        gate = _subscription_gate(session)
        if gate:
            if len(steps) == 2 and steps[1] == "0":
                return con(_main_menu(name))
            return gate
        return end(
            "👨‍🌾 Book Expert Visit\n"
            f"County: {county or 'Not set'}\n"
            "Our team will call you within 24 hrs.\n"
            "Toll-free: 0800 720 999\n"
            "Or email: experts@agritech.ai"
        )

    # ────────────────────────────────────────────────────────────────────────
    # Option 7: Advisory Tips (premium)
    # ────────────────────────────────────────────────────────────────────────
    elif option == "7":
        gate = _subscription_gate(session)
        if gate:
            if len(steps) == 2 and steps[1] == "0":
                return con(_main_menu(name))
            return gate
        if not county:
            return con(f"Set your county first.\n{_county_menu()}")
        return end(_advisory_tips(county, farm_type))

    # ────────────────────────────────────────────────────────────────────────
    # Option 8: My Subscription
    # ────────────────────────────────────────────────────────────────────────
    elif option == "8":
        return end(_subscription_info(session, phone_number))

    # ────────────────────────────────────────────────────────────────────────
    # Option 9: About
    # ────────────────────────────────────────────────────────────────────────
    elif option == "9":
        return end(
            "Agritech AI 🌾\n"
            "AI-powered farm advice for Kenyan farmers.\n"
            "Real-time weather + satellite data +\n"
            "local crop & livestock knowledge.\n"
            "Dial *384*12345# anytime."
        )

    return con(_main_menu(name))