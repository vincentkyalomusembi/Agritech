from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from recommender import get_recommendation, MOCK_DATA
from services.alerts import build_weather_alert, build_disease_alert
from services.market import get_market_prices
from services.advisory import build_advice
from services.weather import get_weather
from user_store import get_user_by_phone, list_vets, list_agricultural_officers, update_user
from services.africastalking import notify_subscription
from user_store import subscribe_user
from datetime import datetime


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
    return "CON Select commodity:\n1. Maize\n2. Beans\n3. Sorghum\n4. Millet\n5. Cassava\n6. Goat\n7. Sheep\n8. Chicken\n9. Dairy\n10. Fish"


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


def _local_fast_recommendation(county: str, farm_type: str, soil: str | None, farm_size: str | None, budget: str | None, experience: str | None):
    county = (county or "").strip().title()
    farm_type = (farm_type or "crop").strip().lower()
    soil = (soil or "loamy").strip().lower()

    region_data = MOCK_DATA.get("regions", {}).get(
        county,
        {
            "soil": "loamy",
            "crop_recommendation": "maize",
            "livestock_recommendation": "chicken",
        },
    )

    recommendation = region_data["livestock_recommendation"] if farm_type in {"animal", "livestock"} else region_data["crop_recommendation"]
    options = [recommendation]

    if farm_type in {"animal", "livestock"}:
        if recommendation == "goat":
            options = ["goat", "sheep", "chicken", "dairy cattle"]
        elif recommendation == "dairy cattle":
            options = ["dairy cattle", "goat", "chicken", "sheep"]
        else:
            options = [recommendation, "goat", "sheep", "chicken"]
    else:
        if recommendation == "maize":
            options = ["maize", "beans", "cowpea", "sorghum"]
        elif recommendation == "sorghum":
            options = ["sorghum", "millet", "cowpea", "cassava"]
        else:
            options = [recommendation, "maize", "beans", "sorghum"]

    weather_text = "Weather data temporarily unavailable; using cached guidance."
    advice = (
        f"Based on {county} with {soil} soil, {recommendation} is recommended. "
        f"Best options: {', '.join(options)}. "
        f"Keep monitoring rainfall, soil moisture, and local pest pressure."
    )

    return {
        "county": county,
        "soil": soil,
        "farm_type": farm_type,
        "recommendation": recommendation,
        "recommendation_options": options,
        "advice": advice,
        "weather": {"condition": weather_text, "temp": "?", "source": "fallback"},
        "gee_insights": None,
        "farm_size": farm_size,
        "budget": budget,
        "experience": experience,
    }


def _get_recommendation_safe(county: str, farm_type: str, soil: str | None, farm_size: str | None, budget: str | None, experience: str | None):
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        get_recommendation,
        county,
        farm_type,
        soil,
        farm_size,
        budget,
        experience,
        True,
    )
    try:
        return future.result(timeout=3)
    except FuturesTimeoutError:
        return _local_fast_recommendation(county, farm_type, soil, farm_size, budget, experience)
    except Exception:
        return _local_fast_recommendation(county, farm_type, soil, farm_size, budget, experience)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _format_weather_summary(weather: dict):
    parts = [
        f"Weather: {weather.get('condition', 'Unknown')}",
        f"Temp: {weather.get('temp', '?')}°C",
    ]
    if weather.get("feels_like") is not None:
        parts.append(f"Feels like: {weather.get('feels_like')}°C")
    if weather.get("humidity") is not None:
        parts.append(f"Humidity: {weather.get('humidity')}%")
    if weather.get("wind_speed") is not None:
        parts.append(f"Wind: {weather.get('wind_speed')} m/s")
    return " | ".join(parts)


def _format_options(options):
    items = [opt for opt in (options or []) if opt]
    if not items:
        return "Options: n/a"
    pretty = ", ".join(item.title() for item in items[:4])
    return f"Options: {pretty}"


def _quick_alert_summary(weather: dict, gee_insights: dict | None, farm_type: str):
    temp = weather.get("temp")
    humidity = weather.get("humidity")
    condition = str(weather.get("condition", "")).lower()
    alert_level = (gee_insights or {}).get("alert_level", "unknown") if gee_insights else "unknown"

    if farm_type in {"animal", "livestock"}:
        if isinstance(temp, (int, float)) and temp >= 30:
            return "Alert: high heat stress risk; provide shade and clean water."
        if isinstance(humidity, (int, float)) and humidity >= 80:
            return "Alert: high humidity risk; watch for animal disease pressure."
        if alert_level == "high":
            return "Alert: dry forage risk; secure feed and water early."
        return "Alert: monitor animal health and water supply closely."

    if isinstance(temp, (int, float)) and temp >= 30:
        return "Alert: heat and moisture stress risk; mulch and conserve water."
    if isinstance(humidity, (int, float)) and humidity >= 80:
        return "Alert: fungal disease risk is higher in humid weather."
    if alert_level == "high":
        return "Alert: drought stress risk; use drought-tolerant practices."
    if "rain" in condition:
        return "Alert: manage drainage and fungal disease scouting."
    return "Alert: continue regular field scouting and weather checks."


def _get_advisory_tips_seasonal(phone_number: str = ""):
    """Get tips specific to current season and farm type"""
    current_month = datetime.now().month
    user = get_user_by_phone(phone_number)
    farm_type = user.get("farm_type", "crop") if user else "crop"
    
    # Determine season (Kenya tropical: dry Jan-Feb, 6-8; rainy Mar-5, 9-11; Dec mixed)
    if current_month in [1, 2, 6, 7, 8]:
        season = "dry"
    elif current_month in [3, 4, 5, 9, 10, 11]:
        season = "rainy"
    else:
        season = "transition"
    
    # Season & farm-type specific tips
    if farm_type == "livestock":
        tips_by_season = {
            "dry": "Livestock Tips (Dry Season):\n• Ensure enough water for animals\n• Provide quality hay/fodder\n• Supplement with mineral licks\n• Monitor heat stress\n• Increase feed portions",
            "rainy": "Livestock Tips (Rainy Season):\n• Prevent waterborne diseases\n• Improve shelter drainage\n• Vaccinate against seasonal diseases\n• Manage pasture rotation\n• Check for parasites",
            "transition": "Livestock Tips (Transition):\n• Adjust feed gradually\n• Check animal health status\n• Plan breeding season\n• repair shelters & fences\n• Monitor weather changes",
        }
    else:
        tips_by_season = {
            "dry": "Crop Tips (Dry Season):\n• Use drought-resistant varieties\n• Practice mulching\n• Improve water retention\n• Plan irrigation\n• Collect rainwater",
            "rainy": "Crop Tips (Rainy Season):\n• Prepare land in advance\n• Use quality seeds\n• Practice proper spacing\n• Manage crop diseases\n• Monitor soil drainage",
            "transition": "Crop Tips (Transition):\n• Prepare land for next season\n• Clear previous crop residue\n• Test soil nutrients\n• Plan crop rotation\n• Update farm tools",
        }
    
    return tips_by_season.get(season, "Agricultural Tips:\n• Test soil before planting\n• Use certified seeds\n• Apply fertilizer at right time\n• Monitor weather regularly\n• Practice crop rotation")


def _get_county_or_ask(phone_number: str, parts: list):
    """If user has county in profile, auto-use it. Otherwise ask."""
    user = get_user_by_phone(phone_number)
    if len(parts) == 1:
        # First call for this option
        if user and user.get("county"):
            # Auto-use profile county
            return (f"Using your county: {user.get('county')}", user.get("county"))
        else:
            # Ask for county
            return ("CON Enter your county for alerts (e.g., Makueni):", None)
    else:
        # County provided
        county = parts[1]
        return (None, county)


def _profile_edit_flow(phone_number: str, parts: list):
    """Handle profile edit sub-menu flow"""
    user = get_user_by_phone(phone_number)
    if not user:
        return "END Profile not found. Contact admin to register."
    
    if len(parts) == 1:
        # Show profile and edit menu
        return (
            f"CON Current profile:\n"
            f"1. Name: {user.get('name', 'N/A')}\n"
            f"2. County: {user.get('county', 'N/A')}\n"
            f"3. Farm Type: {user.get('farm_type', 'N/A')}\n"
            f"4. Soil Type: {user.get('soil_type', 'N/A')}\n"
            f"Select field to edit (1-4):"
        )
    elif len(parts) == 2:
        # Which field to edit
        field_choice = parts[1]
        if field_choice == "1":
            return "CON Enter your name:"
        elif field_choice == "2":
            return "CON Enter your county:"
        elif field_choice == "3":
            return "CON Enter farm type (crop/livestock):"
        elif field_choice == "4":
            return "CON Enter soil type (loamy/sandy/clay):"
        else:
            return "END Invalid choice"
    elif len(parts) == 3:
        # Field choice and new value
        field_choice = parts[1]
        new_value = parts[2]
        
        updates = {}
        field_name = ""
        
        if field_choice == "1":
            updates["name"] = new_value
            field_name = "Name"
        elif field_choice == "2":
            updates["county"] = new_value
            field_name = "County"
        elif field_choice == "3":
            updates["farm_type"] = new_value.lower()
            field_name = "Farm Type"
        elif field_choice == "4":
            updates["soil_type"] = new_value.lower()
            field_name = "Soil Type"
        else:
            return "END Invalid choice"
        
        update_user(phone_number, updates)
        return f"END {field_name} updated successfully!"
    
    return "END Invalid input"


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
            response = _get_recommendation_safe(county, "crop", soil_input, farm_size=farm_size, budget=budget, experience=experience)
            alert_summary = _quick_alert_summary(response.get("weather", {}), response.get("gee_insights"), "crop")
            return (
                f"END Recommended for {response['county']}:\n"
                f"• {response['recommendation'].title()}\n"
                f"• {_format_options(response.get('recommendation_options'))}\n"
                f"• {_format_weather_summary(response['weather'])}\n"
                f"• {alert_summary}\n"
                f"Advice: {response['advice'][:100]}..."
            )

    # Livestock Recommendation (Option 2)
    elif option == "2":
        # flow: 2 -> county -> herd size -> farm size -> budget -> experience
        if len(parts) == 1:
            return "CON Enter your county (e.g., Makueni):"
        elif len(parts) == 2:
            return "CON Enter herd size (small/medium/large) or type 'unknown':"
        elif len(parts) == 3:
            return "CON Enter your farm size (e.g., 2 acres or 0.5 ha):"
        elif len(parts) == 4:
            return "CON Enter your budget in KES (approx):"
        elif len(parts) == 5:
            return "CON Select experience level:\n1. Beginner\n2. Intermediate\n3. Expert"
        elif len(parts) >= 6:
            county = parts[1]
            herd_size = parts[2]
            farm_size = parts[3]
            budget = parts[4]
            exp_choice = parts[5]
            exp_map = {"1": "beginner", "2": "intermediate", "3": "expert"}
            experience = exp_map.get(exp_choice, exp_choice)
            herd_input = None if herd_size.lower() == "unknown" else herd_size
            response = _get_recommendation_safe(county, "livestock", herd_input, farm_size=farm_size, budget=budget, experience=experience)
            alert_summary = _quick_alert_summary(response.get("weather", {}), response.get("gee_insights"), "livestock")
            return (
                f"END Recommended for {response['county']}:\n"
                f"• {response['recommendation'].title()}\n"
                f"• {_format_options(response.get('recommendation_options'))}\n"
                f"• {_format_weather_summary(response['weather'])}\n"
                f"• {alert_summary}\n"
                f"Advice: {response['advice'][:100]}..."
            )

    # Weather Alerts (Option 3)
    elif option == "3":
        status, county = _get_county_or_ask(phone_number, parts)
        if status and status.startswith("Using"):
            # Auto-filled county
            if not _is_subscribed(phone_number):
                return "END Weather alerts for subscribed users only. Reply with option 9 to subscribe."
            return f"END {_get_weather_alerts(county, subscribed=True)}"
        elif status:
            # Asking for county
            return status
        else:
            # County was provided in parts[1]
            if not _is_subscribed(phone_number):
                return "END Weather alerts for subscribed users only. Reply with option 9 to subscribe."
            return f"END {_get_weather_alerts(county, subscribed=True)}"

    # Disease Alerts (Option 4)
    elif option == "4":
        status, county = _get_county_or_ask(phone_number, parts)
        if status and status.startswith("Using"):
            # Auto-filled county
            if not _is_subscribed(phone_number):
                return "END Disease alerts for subscribed users only. Reply with option 9 to subscribe."
            return f"END {_get_disease_alerts(county, subscribed=True)}"
        elif status:
            # Asking for county
            return status
        else:
            # County was provided in parts[1]
            if not _is_subscribed(phone_number):
                return "END Disease alerts for subscribed users only. Reply with option 9 to subscribe."
            return f"END {_get_disease_alerts(county, subscribed=True)}"

    # Market Prices (Option 5)
    elif option == "5":
        if len(parts) == 1:
            return _get_market_prices_menu()
        elif len(parts) == 2:
            commodity_map = {
                "1": "maize", "2": "beans", "3": "sorghum", "4": "millet",
                "5": "cassava", "6": "goat", "7": "sheep", "8": "chicken",
                "9": "dairy", "10": "fish"
            }
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
        tips = _get_advisory_tips_seasonal(phone_number)
        return f"END {tips}"

    # My Profile (Option 8)
    elif option == "8":
        profile_response = _profile_edit_flow(phone_number, parts)
        if profile_response.startswith("CON"):
            return profile_response
        else:
            return profile_response

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