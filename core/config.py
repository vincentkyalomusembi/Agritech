"""
All environment and app-wide settings live here
"""


import os
from pathlib import path
from dotenv import load_dotenv


#load .env from the project root
BASE_DIR = path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")



class Settings:
    # Africa's talking
    AT_USENAME = os.getenv("AT_USERNAME", "sandbox")