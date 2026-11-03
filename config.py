"""
Projekti teema: CineMeteo - Ilmast sõltuv meediaplaneerija
Fail: config.py
Kirjeldus: Keskkonnamuutujate laadimine ja globaalsete seadete hoidmine.
"""

import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "cinemeteo.db")
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Tartu")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")