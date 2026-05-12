"""
app.py 
application start point


"""

import uvicorn
from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware


from core.config import settings 
from routes.ussd import router as used_router
from routes.recommend import router as recommend_router



app = FastAPI(
    title="Agritech API",
    description="AI-powered farm advisory for Kenyan farmers via USSD, SMS and web.",
    version="0.2.0",

)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_priduction else [
        "https://agritech.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#routers
app.include_router(used_router)
app.include_router(recommend_router)

#health check
@app.get("/", tags=["health"])

def root():
    return {"status":"Agritech AI running", "version":"0.2.0", "env":settings.APP_ENV}


@app.get("/health", tags=["health"])
def health():
    return {"status":"healthy"}


#local dev entry point
if __name__ == "__main__":
    uvicorn .run("app:app", host="0.0.0.0", port=8000, reload=True)