"""
app.py
Application entry point — stays thin.
All logic lives in routes/, services/, models/, core/, db/.
"""

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routes.ussd import router as ussd_router
from routes.recommend import router as recommend_router


# ── Startup / shutdown ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Init session DB (creates table if missing)
    from db.sessions import init_db, purge_expired
    init_db()
    purge_expired()
    print("[startup] Session DB ready.")

    # 2. Load / auto-train ML model
    from models.recommender import _get_model_bundle
    _get_model_bundle()
    print("[startup] ML model ready.")

    yield
    # Nothing to clean up on shutdown yet


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Agritech AI",
    description="AI-powered farm advisory for Kenyan farmers via USSD, SMS, and web.",
    version="0.2.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else [
        "https://agritech.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(ussd_router)
app.include_router(recommend_router)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/", tags=["health"])
def root():
    return {"status": "Agritech AI running", "version": "0.2.0", "env": settings.APP_ENV}


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}


# ── Local dev ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)