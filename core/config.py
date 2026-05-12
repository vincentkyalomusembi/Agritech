"""
All environment and app-wide settings live here
"""



from os import getenv
import os
from pathlib import Path
from dotenv import load_dotenv


# Load .env from the project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    # Africa's Talking
    AT_USERNAME: str = os.getenv("AT_USERNAME", "sandbox")
    AT_API_KEY: str = os.getenv("AT_API_KEY", "")

    # OpenWeather
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    WEATHER_TIMEOUT_SECS: int = int(os.getenv("WEATHER_TIMEOUT_SECS", "2"))

    # Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Google Earth Engine
    GEE_SERVICE_ACCOUNT: str = os.getenv("GEE_SERVICE_ACCOUNT", "")
    GEE_KEY_FILE: str = os.getenv("GEE_KEY_FILE", "")

    # Database / Supabase
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Auth — JWT
    JWT_SECRET: str           = os.getenv("JWT_SECRET", "")
    JWT_EXPIRES_SECONDS: int  = int(os.getenv("JWT_EXPIRES_SECONDS", "86400"))   # 24 h
    OTP_EXPIRES_SECONDS: int  = int(os.getenv("OTP_EXPIRES_SECONDS", "300"))     # 5 min

    # App
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DATA_DIR: Path = BASE_DIR / "data"
    SEED_DATA_PATH: Path = BASE_DIR / "data" / "seed_data.csv"
    MODEL_PATH: Path = BASE_DIR / "models" / "decision_tree.pkl"
    
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

settings = Settings()