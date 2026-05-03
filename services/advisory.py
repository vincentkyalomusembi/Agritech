import os
import warnings

from dotenv import load_dotenv


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def build_advice(county: str, soil: str, weather: dict, recommendation: str):
    county = (county or "").strip().title()
    soil = (soil or "loamy").strip().lower()
    weather_condition = weather.get("condition", "unknown weather")
    temp = weather.get("temp", "?")

    if not GEMINI_API_KEY:
        return (
            f"Based on {county} with {soil} soil and {weather_condition} weather "
            f"({temp}°C), {recommendation} is recommended."
        )

    try:
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        prompt = (
            f"Explain in 2 short sentences why {recommendation} is suitable for farming in "
            f"{county}, Kenya with {soil} soil and {weather_condition} weather at {temp}°C."
        )
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        if getattr(response, "text", None):
            return response.text.strip()
    except Exception:
        pass

    return (
        f"Based on {county} with {soil} soil, {recommendation} is recommended for the current season."
    )