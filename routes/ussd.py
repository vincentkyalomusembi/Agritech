"""
routes/ussd.py
Africa's Talking USSD callback handler.

Navigation model
----------------
Uses text.split("*") — Africa's Talking always sends the full session path
in `text`, so navigation is stateless. A server restart never drops a user
mid-flow because we never rely on in-memory state for menu position.

    ""          -> user just dialled         -> main menu
    "1"         -> pressed 1 on main menu    -> county list
    "1*3"       -> picked county #3          -> farm type menu
    "1*3*2"     -> picked livestock          -> recommendation + END

Session store (db/sessions.py)
-------------------------------
We DO need server-side state for data that can't live in the menu path:
  - county, farm_type (remembered across dials so we skip asking twice)
  - name (shown in greeting once onboarding is done)
  - onboarded: bool (controls whether onboarding runs on first dial)

This is written to SQLite now (zero deps) and swapped for Supabase in Phase 1
by changing one function in db/sessions.py — nothing here changes.

CON / END rules
---------------
  CON  = session continues, user can press more keys
  END  = session ends, user reads final message and hangs up
  182-char hard limit on CON bodies (Africa's Talking silently truncates)
"""

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from db.sessions import get_session, set_session
from models.recommender import build_recommendation, list_counties
from services.weather import get_weather

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


# ── Onboarding ────────────────────────────────────────────────────────────────
# First-time users complete a short onboarding before seeing the main menu.
# Onboarding path: name -> county -> farm_type
# Stored to session so it's never asked again.

def _needs_onboarding(session: dict) -> bool:
    return not session.get("onboarded", False)


def _handle_onboarding(steps: list, phone_number: str, session: dict) -> PlainTextResponse:
    """
    Onboarding is a linear flow prepended before the main menu.
    steps[0] will be "0" (we route onboarding under a "0*" prefix internally).

    Step count:
      0 steps  -> ask name
      1 step   -> got name, ask county
      2 steps  -> got county, ask farm type
      3 steps  -> complete, save, redirect to main menu
    """
    counties = list_counties()

    if len(steps) == 0:
        return con(
            "Welcome to Agritech AI 🌾\n"
            "Quick setup (3 steps).\n"
            "Enter your name:"
        )

    if len(steps) == 1:
        # Save name, ask county
        set_session(phone_number, {"name": steps[0]})
        county_list = "\n".join(f"{i}. {c}" for i, c in enumerate(counties, 1))
        return con(f"Select your county:\n{county_list}")

    if len(steps) == 2:
        # Save county choice, ask farm type
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
        # Save farm type, mark onboarded
        farm_map = {"1": "crop", "2": "livestock"}
        farm_type = farm_map.get(steps[2])
        if not farm_type:
            return con("Enter 1 for Crop or 2 for Livestock:")
        set_session(phone_number, {"farm_type": farm_type, "onboarded": True})
        session = get_session(phone_number)
        name = session.get("name", "Farmer")
        return con(_main_menu(name))

    return con("Welcome to Agritech AI. Enter your name:")


# ── Main menu ─────────────────────────────────────────────────────────────────

def _main_menu(name: str = "Farmer") -> str:
    return (
        f"Hi {name} 🌾\n"
        "1. Get Recommendation\n"
        "2. My Profile\n"
        "3. About"
    )


# ── County menu ───────────────────────────────────────────────────────────────

def _county_menu() -> str:
    counties = list_counties()
    lines = ["Select your county:"]
    lines += [f"{i}. {c}" for i, c in enumerate(counties, 1)]
    return "\n".join(lines)


# ── Farm type menu ────────────────────────────────────────────────────────────

def _farm_type_menu(county: str) -> str:
    return (
        f"County: {county}\n"
        "Farm type:\n"
        "1. Crop\n"
        "2. Livestock"
    )


# ── Recommendation screen ─────────────────────────────────────────────────────

def _recommendation_screen(county: str, farm_type: str) -> str:
    weather = get_weather(county)
    result = build_recommendation(county, farm_type, weather)

    if not result:
        return f"No data found for {county}. Try again or contact support."

    src = "live" if (weather or {}).get("source") == "openweather" else "est."
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


# ── Profile screen ────────────────────────────────────────────────────────────

def _profile_screen(session: dict) -> str:
    return (
        f"My Profile\n"
        f"Name: {session.get('name', 'N/A')}\n"
        f"County: {session.get('county', 'N/A')}\n"
        f"Farm type: {session.get('farm_type', 'N/A')}\n"
        "1. Edit county\n"
        "2. Edit farm type"
    )


# ── USSD callback ─────────────────────────────────────────────────────────────

@router.post("/ussd", response_class=PlainTextResponse)
async def ussd_callback(request: Request):
    form = await request.form()
    phone_number: str = form.get("phoneNumber", "")
    text: str = form.get("text", "")

    steps = [s for s in text.split("*") if s != ""]
    session = get_session(phone_number)

    # ── Onboarding gate ───────────────────────────────────────────────────
    # New users go through a 3-step onboarding before seeing the main menu.
    if _needs_onboarding(session):
        return _handle_onboarding(steps, phone_number, session)

    name = session.get("name", "Farmer")

    # ── Level 0: main menu ────────────────────────────────────────────────
    if len(steps) == 0:
        return con(_main_menu(name))

    option = steps[0]

    # ── Option 1: Recommendation ──────────────────────────────────────────
    if option == "1":

        # Use saved county if we have it — skip asking
        saved_county = session.get("county")

        if len(steps) == 1:
            if saved_county:
                # Skip county selection — go straight to farm type
                return con(
                    f"County: {saved_county}\n"
                    "Farm type:\n"
                    "1. Crop\n"
                    "2. Livestock\n"
                    "3. Change county"
                )
            else:
                return con(_county_menu())

        if len(steps) == 2:
            if saved_county:
                # steps[1] is farm type choice (or "3" to change county)
                if steps[1] == "3":
                    return con(_county_menu())
                farm_map = {"1": "crop", "2": "livestock"}
                farm_type = farm_map.get(steps[1])
                if not farm_type:
                    return con(f"Enter 1 (Crop) or 2 (Livestock):\n(County: {saved_county})")
                return end(_recommendation_screen(saved_county, farm_type))
            else:
                # steps[1] is county index
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
                # User chose to change county; steps[2] is new county index
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
                # No saved county path: steps[1]=county idx, steps[2]=farm type
                counties = list_counties()
                try:
                    idx = int(steps[1]) - 1
                    if not (0 <= idx < len(counties)):
                        return con(f"Invalid county.\n{_county_menu()}")
                    selected = counties[idx]
                    farm_map = {"1": "crop", "2": "livestock"}
                    farm_type = farm_map.get(steps[2])
                    if not farm_type:
                        return con(f"Enter 1 or 2.\n{_farm_type_menu(selected)}")
                    return end(_recommendation_screen(selected, farm_type))
                except ValueError:
                    return con("Invalid input. Start again.")

        if len(steps) == 4:
            # change-county path: 1*3*<county_idx>*<farm_type>
            counties = list_counties()
            try:
                idx = int(steps[2]) - 1
                if not (0 <= idx < len(counties)):
                    return con(f"Invalid county.\n{_county_menu()}")
                selected = counties[idx]
                farm_map = {"1": "crop", "2": "livestock"}
                farm_type = farm_map.get(steps[3])
                if not farm_type:
                    return con(f"Enter 1 or 2.\n{_farm_type_menu(selected)}")
                return end(_recommendation_screen(selected, farm_type))
            except (ValueError, IndexError):
                return con("Invalid input. Start again.")

    # ── Option 2: Profile ─────────────────────────────────────────────────
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
                # Edit county
                counties = list_counties()
                try:
                    idx = int(steps[2]) - 1
                    if not (0 <= idx < len(counties)):
                        return con(f"Invalid.\n{_county_menu()}")
                    set_session(phone_number, {"county": counties[idx]})
                    return end(f"County updated to {counties[idx]}.")
                except ValueError:
                    return con(f"Enter a number.\n{_county_menu()}")
            elif steps[1] == "2":
                # Edit farm type
                farm_map = {"1": "crop", "2": "livestock"}
                farm_type = farm_map.get(steps[2])
                if not farm_type:
                    return con("Enter 1 (Crop) or 2 (Livestock):")
                set_session(phone_number, {"farm_type": farm_type})
                return end(f"Farm type updated to {farm_type}.")

    # ── Option 3: About ───────────────────────────────────────────────────
    elif option == "3":
        return end(
            "Agritech AI\n"
            "AI-powered farm advice for Kenyan farmers.\n"
            "Real-time weather + satellite data + local crop knowledge.\n"
            "Dial again anytime."
        )

    return con(_main_menu(name))