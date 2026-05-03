from recommender import get_recommendation


def _main_menu():
    return "CON Welcome to Agritech AI\n1. Crop Recommendation\n2. Livestock Recommendation\n3. Subscribe (KES 10/week)"


def handle_ussd(text: str, phone_number: str = ""):
    text = (text or "").strip()

    if not text:
        return _main_menu()

    parts = text.split("*")
    option = parts[0]

    if option in {"1", "2"} and len(parts) == 1:
        return "CON Enter your county (e.g., Makueni):"

    if option in {"1", "2"} and len(parts) == 2:
        return "CON Enter soil type (loamy/sandy/clay) or type 'unknown':"

    if option in {"1", "2"} and len(parts) >= 3:
        county = parts[1]
        soil = parts[2]
        farm_type = "crop" if option == "1" else "livestock"
        soil_input = None if soil.lower() == "unknown" else soil
        response = get_recommendation(county, farm_type, soil_input)
        return (
            f"END Recommended for {response['county']}:\n"
            f"• {response['recommendation']}\n"
            f"Advice: {response['advice'][:100]}..."
        )

    if option == "3":
        return "END Subscription service coming soon."

    return "END Invalid option. Try again."