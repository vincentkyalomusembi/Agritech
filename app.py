from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from urllib.parse import parse_qs
from pathlib import Path
import json
import time

import uvicorn

from recommender import get_recommendation
from services.gee import get_gee_insights
from ussd_flow import handle_ussd
from services.africastalking import send_sms, notify_subscription
from user_store import subscribe_user, get_user_by_phone, list_subscribers


app = FastAPI(title="Agritech AI")
BASE_DIR = Path(__file__).resolve().parent
GEE_CACHE_FILE = BASE_DIR / "data" / "gee_alerts_latest.json"
USSD_DEBUG_LOG = BASE_DIR / "logs" / "ussd_debug.log"


def _log_ussd_event(message: str):
    USSD_DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
    with USSD_DEBUG_LOG.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


class RecommendRequest(BaseModel):
    county: str
    farm_type: str
    soil_type: str | None = None
    farm_size: str | None = None
    budget: str | None = None
    experience: str | None = None


@app.post("/recommend")
def recommend(req: RecommendRequest):
    return get_recommendation(
        req.county,
        req.farm_type,
        req.soil_type,
        farm_size=req.farm_size,
        budget=req.budget,
        experience=req.experience,
    )


@app.post("/ussd", response_class=PlainTextResponse)
async def ussd(request: Request):
    started = time.time()
    body = await request.body()
    parsed = parse_qs(body.decode("utf-8")) if body else {}
    text = parsed.get("text", [""])[0]
    phone_number = parsed.get("phoneNumber", [""])[0]
    result = handle_ussd(text=text, phone_number=phone_number)
    elapsed_ms = int((time.time() - started) * 1000)
    prefix = result[:3] if result else ""
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    safe_phone = f"***{phone_number[-4:]}" if phone_number else "unknown"
    _log_ussd_event(
        f"[{now}] /ussd phone={safe_phone} text_len={len(text)} prefix={prefix} elapsed_ms={elapsed_ms}"
    )
    return PlainTextResponse(result)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/gee/alerts/{county}")
def gee_alerts(county: str):
    return get_gee_insights(county)


@app.get("/gee/alerts-cache")
def gee_alerts_cache():
    if not GEE_CACHE_FILE.exists():
        return {
            "status": "not_found",
            "message": "No cached GEE summaries yet. Run scripts/update_gee_summaries.py first.",
        }
    with GEE_CACHE_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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
