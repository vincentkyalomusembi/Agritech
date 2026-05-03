from recommender import get_recommendation
from services.alerts import get_alerts
from services.market import get_market_prices
from services.advisory import build_advice
from services.weather import get_weather
from user_store import get_user_by_phone, list_vets, list_agricultural_officers


def _main_menu():
    return "CON Welcome to Agritech AI\n1. Crop Recommendation\n2. Livestock Recommendation\n3. Weather Alerts\n4. Disease Alerts\n5. Market Prices\n6. Request Expert Visit\n7. Advisory Tips\n8. My Profile\n9. Subscribe"


def _get_weather_alerts(county: str):
    try:
        weather = get_weather(county)
        alerts = get_alerts(county)
        return f"Weather in {county}: {weather.get('condition', 'Unknown')}, {weather.get('temp', '?')}°C\nAlerts: {' '.join(alerts[:2])}"
    except:
        return f"Weather alerts for {county} service temporarily unavailable"


def _get_disease_alerts(county: str):
    alerts = get_alerts(county)
    return f"Disease alerts for {county}:\n• No active disease outbreaks reported\n• Monitor crops for pests"


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

    if not text:
        return _main_menu()

    parts = text.split("*")
    option = parts[0]

    # Crop Recommendation (Option 1)
    if option == "1":
        if len(parts) == 1:
            return "CON Enter your county (e.g., Makueni):"
        elif len(parts) == 2:
            return "CON Enter soil type (loamy/sandy/clay) or type 'unknown':"
        elif len(parts) >= 3:
            county = parts[1]
            soil = parts[2]
            soil_input = None if soil.lower() == "unknown" else soil
            response = get_recommendation(county, "crop", soil_input)
            return (
                f"END Recommended for {response['county']}:\n"
                f"• {response['recommendation']}\n"
                f"Advice: {response['advice'][:100]}..."
            )

    # Livestock Recommendation (Option 2)
    elif option == "2":
        if len(parts) == 1:
            return "CON Enter your county (e.g., Makueni):"
        elif len(parts) == 2:
            return "CON Enter soil type (loamy/sandy/clay) or type 'unknown':"
        elif len(parts) >= 3:
            county = parts[1]
            soil = parts[2]
            soil_input = None if soil.lower() == "unknown" else soil
            response = get_recommendation(county, "livestock", soil_input)
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
            return f"END {_get_weather_alerts(county)}"

    # Disease Alerts (Option 4)
    elif option == "4":
        if len(parts) == 1:
            return "CON Enter your county for disease alerts:"
        elif len(parts) >= 2:
            county = parts[1]
            return f"END {_get_disease_alerts(county)}"

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
        return "END Subscription service:\n• KES 10/week for premium features\n• Includes weather alerts, market updates\n• Call 07XX123456 to subscribe"

    return "END Invalid option. Try again."