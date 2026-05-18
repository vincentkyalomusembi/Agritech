from fastapi import APIRouter

# These match the metadata in app.py FastAPI(...) constructor
APP_TITLE   = "Agritech AI"
APP_VERSION = "0.2.0"

router = APIRouter()


@router.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": f"{APP_TITLE} Backend Running",
        "version": APP_VERSION,
    }


@router.get("/health")
async def health():
    """Health check for deployment"""
    return {"status": "healthy"}
