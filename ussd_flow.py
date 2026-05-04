from recommender import get_recommendation
from services.alerts import build_weather_alert, build_disease_alert
from services.market import get_market_prices
from services.advisory import build_advice
from services.weather import get_weather
from user_store import get_user_by_phone, list_vets, list_agricultural_officers
from services.africastalking import notify_subscription
from user_store import subscribe_user


def _main_menu(user_name: str | None = None):
    greeting_name = (user_name or "").strip() or "Farmer"
    return (
        f"CON Welcome {greeting_name} in Agritech AI\n"
        "1. Crop Recommendation\n"
        "2. Livestock Recommendation\n"
        "3. Weather Alerts\n"
        "4. Disease Alerts\n"
        "5. Market Prices\n"
        "6. Request Expert Visit\n"
        "7. Advisory Tips\n"
        "8. My Profile\n"
        "9. Subscribe"
    )


def _is_subscribed(phone_number: str):
    user = get_user_by_phone(phone_number)
    return bool(user and user.get("subscribed"))


def _get_weather_alerts(county: str, subscribed: bool = False):
    try:
        weather = get_weather(county)
        alert_text = build_weather_alert(county, subscribed=subscribed)
        return (
            f"Weather in {county}: {weather.get('condition', 'Unknown')}, {weather.get('temp', '?')}°C\n"
            f"{alert_text}"
        )
    except Exception:
        return f"Weather alerts for {county} service temporarily unavailable"


def _get_disease_alerts(county: str, subscribed: bool = False):
    return build_disease_alert(county, subscribed=subscribed)


def _get_market_prices_menu():
    return "CON Select commodity:\n1. Maize\n2. Beans\n3. Goat\n4. Dairy"


def _get_market_price(commodity: str):
    prices = get_market_prices(commodity)
    return f"Market Prices - {commodity.title()}:\n• Min: KES {prices['min']}\n• Max: KES {prices['max']}\n• Unit: {prices['unit']}"


def _get_expert_visit_menu():
    return "CON Select expert type:\n1. Veterinary Officer\n2. Agricultural Officer"


def _get_expert_list(expert_type: str, county: str = ""):
    if expert_type == "1":
        experts = list_vets()[:3]  # Show first 3 vets
        expert_list = "\n".join([f"• {e['name']} - {e['county']}" for e in experts])
        return f"Available Veterinary Officers:\n{expert_list}\n\nCall for appointment"
    else:
        experts = list_agricultural_officers()[:3]  # Show first 3 officers
        expert_list = "\n".join([f"• {e['name']} - {e['county']}" for e in experts])
        return f"Available Agricultural Officers:\n{expert_list}\n\nCall for appointment"


def _get_advisory_tips():
    return "Agricultural Tips:\n• Test soil before planting\n• Use certified seeds\n• Apply fertilizer at right time\n• Monitor weather regularly\n• Practice crop rotation"


def _get_user_profile(phone_number: str):
    user = get_user_by_phone(phone_number)
    if user:
        return f"Profile:\n• Name: {user.get('name', 'Unknown')}\n• County: {user.get('county', 'Unknown')}\n• Farm Type: {user.get('farm_type', 'Unknown')}\n• Soil: {user.get('soil_type', 'Unknown')}"
    else:
        return "Profile not found. Register as new user to access personalized services"


def handle_ussd(text: str, phone_number: str = ""):
    text = (text or "").strip()

    current_user = get_user_by_phone(phone_number)
    user_name = current_user.get("name") if current_user else None

    if not text:
        return _main_menu(user_name)

    parts = text.split("*")
    option = parts[0]

    # Crop Recommendation (Option 1)
    if option == "1":
        # flow: 1 -> county -> soil -> farm size -> budget -> experience
        if len(parts) == 1:
            return "CON Enter your county (e.g., Makueni):"
        elif len(parts) == 2:
            return "CON Enter soil type (loamy/sandy/clay) or type 'unknown':"
        elif len(parts) == 3:
            return "CON Enter your farm size (e.g., 2 acres or 0.5 ha):"
        elif len(parts) == 4:
            return "CON Enter your budget in KES (approx):"
        elif len(parts) == 5:
            return "CON Select experience level:\n1. Beginner\n2. Intermediate\n3. Expert"
        elif len(parts) >= 6:
            county = parts[1]
            soil = parts[2]
            farm_size = parts[3]
            budget = parts[4]
            exp_choice = parts[5]
            exp_map = {"1": "beginner", "2": "intermediate", "3": "expert"}
            experience = exp_map.get(exp_choice, exp_choice)
            soil_input = None if soil.lower() == "unknown" else soil
            response = get_recommendation(county, "crop", soil_input, farm_size=farm_size, budget=budget, experience=experience)
            return (
                f"END Recommended for {response['county']}:\n"
                f"• {response['recommendation']}\n"
                f"Advice: {response['advice'][:100]}..."
            )

    # Livestock Recommendation (Option 2)
    elif option == "2":
        # flow: 2 -> county -> soil -> farm size -> budget -> experience
        if len(parts) == 1:
            return "CON Enter your county (e.g., Makueni):"
        elif len(parts) == 2:
            return "CON Enter soil type (loamy/sandy/clay) or type 'unknown':"
        elif len(parts) == 3:
            return "CON Enter your farm size (e.g., 2 acres or 0.5 ha):"
        elif len(parts) == 4:
            return "CON Enter your budget in KES (approx):"
        elif len(parts) == 5:
            return "CON Select experience level:\n1. Beginner\n2. Intermediate\n3. Expert"
        elif len(parts) >= 6:
            county = parts[1]
            soil = parts[2]
            farm_size = parts[3]
            budget = parts[4]
            exp_choice = parts[5]
            exp_map = {"1": "beginner", "2": "intermediate", "3": "expert"}
            experience = exp_map.get(exp_choice, exp_choice)
            soil_input = None if soil.lower() == "unknown" else soil
            response = get_recommendation(county, "livestock", soil_input, farm_size=farm_size, budget=budget, experience=experience)
            return (
                f"END Recommended for {response['county']}:\n"
                f"• {response['recommendation']}\n"
                f"Advice: {response['advice'][:100]}..."
            )

    # Weather Alerts (Option 3)
    elif option == "3":
        if len(parts) == 1:
            return "CON Enter your county for weather alerts:"
        elif len(parts) >= 2:
            county = parts[1]
            if not _is_subscribed(phone_number):
                return "END Weather alerts are for subscribed users only. Reply with option 9 to subscribe."
            return f"END {_get_weather_alerts(county, subscribed=True)}"

    # Disease Alerts (Option 4)
    elif option == "4":
        if len(parts) == 1:
            return "CON Enter your county for disease alerts:"
        elif len(parts) >= 2:
            county = parts[1]
            if not _is_subscribed(phone_number):
                return "END Disease alerts are for subscribed users only. Reply with option 9 to subscribe."
            return f"END {_get_disease_alerts(county, subscribed=True)}"

    # Market Prices (Option 5)
    elif option == "5":
        if len(parts) == 1:
            return _get_market_prices_menu()
        elif len(parts) == 2:
            commodity_map = {"1": "maize", "2": "beans", "3": "goat", "4": "dairy"}
            commodity = commodity_map.get(parts[1], "maize")
            return f"END {_get_market_price(commodity)}"

    # Request Expert Visit (Option 6)
    elif option == "6":
        if len(parts) == 1:
            return _get_expert_visit_menu()
        elif len(parts) >= 2:
            return f"END {_get_expert_list(parts[1])}"

    # Advisory Tips (Option 7)
    elif option == "7":
        return f"END {_get_advisory_tips()}"

    # My Profile (Option 8)
    elif option == "8":
        return f"END {_get_user_profile(phone_number)}"

    # Subscribe (Option 9)
    elif option == "9":
        if phone_number:
            user = subscribe_user(phone_number, "weekly")
            try:
                notify_subscription(phone_number, "weekly")
            except Exception:
                pass
            return (
                f"END You are now subscribed using {phone_number}.\n"
                f"You will receive weather and disease alerts."
            )
        return "END Subscription service unavailable."

    return "END Invalid option. Try again."