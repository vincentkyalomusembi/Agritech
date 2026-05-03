from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from urllib.parse import parse_qs

import uvicorn

from recommender import get_recommendation
from ussd_flow import handle_ussd
from services.africastalking import send_sms, notify_subscription
from user_store import subscribe_user, get_user_by_phone, list_subscribers


app = FastAPI(title="Agritech AI")


class RecommendRequest(BaseModel):
    county: str
    farm_type: str
    soil_type: str | None = None


@app.post("/recommend")
def recommend(req: RecommendRequest):
    return get_recommendation(req.county, req.farm_type, req.soil_type)


@app.post("/ussd", response_class=PlainTextResponse)
async def ussd(request: Request):
    body = await request.body()
    parsed = parse_qs(body.decode("utf-8")) if body else {}
    text = parsed.get("text", [""])[0]
    phone_number = parsed.get("phoneNumber", [""])[0]
    return PlainTextResponse(handle_ussd(text=text, phone_number=phone_number))


@app.get("/health")
def health():
    return {"status": "ok"}


class SMSRequest(BaseModel):
    to: str
    message: str


@app.post("/sms")
def sms_send(req: SMSRequest):
    """Send SMS using Africa's Talking credentials in the environment."""
    result = send_sms(req.to, req.message)
    return result


class SubscribeRequest(BaseModel):
    phone: str
    plan: str | None = "weekly"


@app.post("/subscribe")
def subscribe(req: SubscribeRequest):
    user = subscribe_user(req.phone, req.plan or "weekly")
    # notify via SMS (best-effort)
    try:
        notify_subscription(req.phone, req.plan or "weekly")
    except Exception:
        pass
    return {"status": "subscribed", "user": user}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
