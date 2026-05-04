import os
import warnings

from dotenv import load_dotenv


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def _gee_context_text(gee_insights: dict | None):
    if not gee_insights or gee_insights.get("status") != "ok":
        return ""

    metrics = gee_insights.get("metrics", {})
    ndvi = metrics.get("ndvi_mean")
    rainfall_anomaly = metrics.get("rainfall_anomaly_pct")
    alert_level = gee_insights.get("alert_level", "unknown")
    return (
        f" Satellite indicators show NDVI {ndvi} and rainfall anomaly {rainfall_anomaly}%."
        f" Current remote-sensing alert level is {alert_level}."
    )


def build_advice(
    county: str,
    soil: str,
    weather: dict,
    recommendation: str,
    gee_insights: dict | None = None,
    farm_size: str | None = None,
    budget: str | None = None,
    experience: str | None = None,
):
    county = (county or "").strip().title()
    soil = (soil or "loamy").strip().lower()
    weather_condition = weather.get("condition", "unknown weather")
    temp = weather.get("temp", "?")
    gee_context = _gee_context_text(gee_insights)

    extra = ""
    if farm_size:
        extra += f" Farm size: {farm_size}."
    if budget:
        extra += f" Budget: KES {budget}."
    if experience:
        extra += f" Experience: {experience}."

    if not GEMINI_API_KEY:
        return (
            f"Based on {county} with {soil} soil and {weather_condition} weather "
            f"({temp}°C), {recommendation} is recommended.{gee_context}{extra}"
        )

    try:
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        prompt = (
            f"Explain in 2 short sentences why {recommendation} is suitable for farming in "
            f"{county}, Kenya with {soil} soil and {weather_condition} weather at {temp}°C."
            f" Include one actionable risk-management tip.{gee_context}"
        )
        if farm_size:
            prompt += f" The farmer has {farm_size} of land."
        if budget:
            prompt += f" Their budget is approximately KES {budget}."
        if experience:
            prompt += f" Experience level: {experience}."
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        if getattr(response, "text", None):
            return response.text.strip()
    except Exception:
        pass

    return (
        f"Based on {county} with {soil} soil, {recommendation} is recommended for the current season."
        f"{gee_context}"
    )