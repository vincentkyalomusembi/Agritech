from fastapi import APIRouter
from core.config import APP_TITLE, APP_VERSION

router = APIRouter()

@router.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": f"{APP_TITLE} Backend Running", 
        "version": APP_VERSION
    }

@router.get("/health")
async def health():
    """Health check for deployment"""
    return {"status": "healthy"}
