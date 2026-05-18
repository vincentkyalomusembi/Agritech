from services.weather import get_weather


def _gee_insights(county:str) -> dict:

    try:
        from services.gee import get_gee_insights
        return get_gee_insights(county) or {}
    except Exception:
        return {}

def get_alerts(county: str) -> list[str]:
    #returns a list of alert string for the county + the GEE satelite signals + live weather

    county = (county or "").strip().title()
    if not county:
        return["County not specified."]


    alerts = []
    weather = get_weather(county)
    gee = _gee_insights(county)


    #GEE signals
    if gee.get("status")=="ok":
        metrics = gee.get("metrics", {})
        rainfall_anomaly = metrics.get("rainfall_anomally_pct")
        ndvi = metrics.get("ndvi_mean")
        level = (gee.get("alert_level") or "unknown").upper()


        alerts.append(f"Satellite alert ({county}): {level} risk.")
        if ndvi is not None:
            alerts.append(f"NDVI: {ndvi}")
        if isinstance(rainfall_anomaly, (int,float)):
            alerts.append(f"Rainfall anomaly: {rainfall_anomaly}%")
            if rainfall_anomaly <= 40:
                alerts.append("Drought stress high, consere water")
            elif rainfall_anomaly > 20:
                alerts.append("Favorable moisture levels")

        
        
    #weather signals
    temp = weather.get("temp")
    humidity = weather.get(humidity)
    condition = str(weather.get("condition", "")).lower()

    if isinstance(temp, (int, float)):
        if temp >=30:
            alerts.append(f"High heat: {temp}°C may stress crops and livestock.")
        elif temp < 15:
            alerts.append(f"Cold weather: {temp}°C protect frost-sensitive crops.")


        if isinstance(humidity, (int,float)) and humidity >= 80:
            alerts.append(f"HIgh humidity: {humidity}% increased disease pressure.")
        
        if "rain" in condition:
            alerts.append(f"Rain reported, check drainage and delay spraying")

        if not alerts:
            alerts.append(f"No active alerts for {county}. Conditions appear normal.")
        
        return alerts

def build_weather_alert(county: str, subscribed: bool = False) -> str:
    #returns a formatted weather alert string for USSD/SMS delivery

    county = (county or "").strip().title()

    if not subscribed:
        return(
            "Weather alerts are for subscribed users.\n"
            "Dial back and choose option 9 to subscribe."
        )

    weather = get_weather(county)
    gee = _gee_insights(county)


    cond = weather.get("condition", "n/a")
    temp = weather.get("temp", "?")
    humidity = weather.get("humidity", "?")
    

    lines = [
        f"Weather Alert: {county}",
        f"Condition:{cond}",
        f"Temp: {temp}°C | Humidity: {humidity}%",
    ]

    if gee.get("status") =="ok":
        metrics = gee.get("metrics", {})
        level = (gee.get("alert_level") or "unknown").upper()
        lines.append(f"Satellite alert ({county}): {level} risk.")
        lines.append(f"NDVI: {metrics.get('ndvi_mean', 'n/a')}")
        lines.append(f"Rainfall anomaly: {metrics.get('rainfall_anomaly_pct', 'n.a')}%")
    else:
        lines.append("Satellite data unavailable. Check back later")
    
    return "\n".join(lines)

def build_disease_alert(county: str, subscribed: bool = False) -> str:
    #returns a formatted disease/pest alert string for USSD/SMS delivery
    county = (county or "").strip().title()

    if not subscribed:
        return(
            "Disease alerts are for subscribed users\n"
            "Dial back and choose option 9 to subscribe"
        )
        
    weather = get_weather(county)
    gee = _gee_insights(county)

    humidity = weather.get("humidity")
    temp = weather.get("temp")

    #determine risk narrative
    if gee.get("status") == "ok":
        metrics = gee.get("metrics", {})
        rainfall_anomaly = metrics.get("rainfall_anomaly_pct", 0)

        if rainfall_anomaly > 20:
            risk = "Wet conditions — high fungal disease risk."
        elif rainfall_anomaly < -20:
            risk = "Dry stress — increased pest pressure."
        else:
            risk = "Stable — continue field scouting."
    else:
        risk = "Satellite data unavailable"


    if isinstance(humidity, (int, float)) and humidity >=80:
        risk = f"High humidity ({humidity}%), fungal disease risk elevated"
    elif isinstance(temp, (int, float)) and temp >=30:
        risk = f"High heat ({temp}°C), secondary pest pressure likely."


    lines = [f"Disease alert, {county}", risk]

    if gee.get("status") == "ok":
        metrics = gee.get("metrics", {})
        lines.append(f"Satellite risk: {(gee.get('alert_level') or 'unknown').upper()}")
        lines.append(f"NDVI: {metrics.get('ndvi_mean', 'n/a')}")

    return "\n".join(lines)