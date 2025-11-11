# app.py
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
from simple_ai import get_recommendation

app = FastAPI(title="Agritech Demo")

# Demo /recommend endpoint (used by USSD handler)
class RecommendRequest(BaseModel):
    county: str
    farm_type: str
    soil_type: str = None

@app.post("/recommend")
def recommend(req: RecommendRequest):
    print(f"DEBUG: Received request: {req}")
    county = req.county.title()
    farm_type = req.farm_type.lower()
    soil = req.soil_type or "loamy"  # default soil type
    
    print(f"DEBUG: Processing - County: {county}, Farm: {farm_type}, Soil: {soil}")
    
    # Get complete recommendation with weather and AI
    result = get_recommendation(county, farm_type, soil)
    
    return result

# USSD simulation endpoint (Africa's Talking posts here in sandbox)
# Africa's Talking sends fields like sessionId, serviceCode, phoneNumber, text
@app.post("/ussd", response_class=PlainTextResponse)
async def ussd(request: Request):
    # Get raw body and parse manually
    body = await request.body()
    body_str = body.decode('utf-8')
    
    # Parse form data manually
    data = {}
    if body_str:
        pairs = body_str.split('&')
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                from urllib.parse import unquote_plus
                data[key] = unquote_plus(value)
    sessionId = data.get("sessionId") or "demo-session"
    phoneNumber = data.get("phoneNumber") or data.get("phone") or "+254700000000"
    text = data.get("text", "")  # text contains the sequence like "1*Machakos*loamy"
    # Parse the USSD text flow (simple approach)
    if text == "" or text is None:
        # show main menu
        resp = "CON Welcome to Agritech AI\n1. Crop Recommendation\n2. Livestock Recommendation\n3. Subscribe (KES 10/week)"
        return PlainTextResponse(resp)
    parts = text.split("*")
    # If user selected option but not inputs
    if parts[0] in ["1", "2"] and len(parts) == 1:
        # ask for county
        return PlainTextResponse("CON Enter your county (e.g., Makueni):")
    # If user selected option and entered county
    if parts[0] in ["1","2"] and len(parts) == 2:
        return PlainTextResponse("CON Enter soil type (loamy/sandy/clay) or type 'unknown':")
    # If final input present (option*county*soil)
    if parts[0] in ["1","2"] and len(parts) >= 3:
        opt = parts[0]
        county = parts[1]
        soil = parts[2]
        farm_type = "crop" if opt == "1" else "animal"
        # Get recommendation
        soil_input = None if soil.lower()=='unknown' else soil
        response = get_recommendation(county, farm_type, soil_input)
        # Build final message (short)
        message = f"END Recommended for {response['county']}:\n• {response['recommendation']}\nAdvice: {response['advice'][:100]}..."
        return PlainTextResponse(message)
    # Fallback
    return PlainTextResponse("END Invalid option. Try again.")

@app.get("/health")
def health():
    return {"status":"ok"}
    
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
