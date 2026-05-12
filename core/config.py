"""
All environment and app-wide settings live here
"""



from os import getenv
import os
from pathlib import path
from dotenv import load_dotenv


#load .env from the project root
BASE_DIR = path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")



class Settings:
    # Africa's talking
    AT_USENAME = os.getenv("AT_USERNAME", "sandbox")
    AT_API_KEY = os.getenv("AT_API_KEY", "")

    #oPEN WEATHER
    OPENWEATHER_API_KEY = os,getenv("OPENWEATHER_API_KEY", "")
    WEATHER_TIMEOUT_SECS:int = int(os.getenv("WEATHER_TIMEOUT_SECS", "2"))

    #Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    #Google Earth Engine
    GEE_SERVICE_ACCOUNT: str = os.getenv("GEE_SERVICE_ACCOUNT", "")
    GEE_KEY_FILE = os.getenv("GEE_KEY_FILE", "")

    #Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPABASE_URL:str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    #App
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DATA_DIR: str = BASE_DIR / "data"
    SEED_DATA_PATH: Path = BASE_DIR / "data" / "seed_data.csv"
    MODEL_PATH: Path = BASE_DIR / "models" / "decision_tree.pkl"
    
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

settings = Settings()