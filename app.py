from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from urllib.parse import parse_qs

import uvicorn

from recommender import get_recommendation
from ussd_flow import handle_ussd


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


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
