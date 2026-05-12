"""
db/county_data.py
Master dataset — all 47 Kenyan counties.

Sources
-------
- Rainfall / temperature means: Kenya Meteorological Department (KMD)
  "Climate Data Normals 1981–2010" and county climate summaries.
- Soil classification: KALRO county soil-profile reports (2018/2019)
  and the Kenya Soil Survey (National Atlas Vol. 4).
- Recommendations: KALRO "Recommended Varieties & Husbandry Practices"
  bulletins, cross-checked against avg rainfall thresholds:
    crop  : ≥800 mm → maize/beans; 400–799 → sorghum/millet; <400 → green_grams
    livestock: arid/semi-arid → camel/goat; highland/medium → dairy_cow/chicken

Soil types used (matching ML model encoding)
--------------------------------------------
  sandy  — Arenosols, Regosols (arid/coastal)
  loamy  — Cambisols, Phaeozems (highland / mixed)
  clay   — Vertisols, Luvisols (Rift, western lowlands)
  peaty  — Histosols (Kakamega, Kisumu wetlands)

avg_rainfall: annual mean (mm)
avg_temp    : annual mean (°C)
"""

from __future__ import annotations

# Each dict has two rows: one for "crop" and one for "livestock".
# Columns: county, soil_type, avg_rainfall, avg_temp, farm_type, recommendation

COUNTY_PROFILES: list[dict] = [
    # ── Coast ────────────────────────────────────────────────────────────────
    {"county": "Mombasa",    "soil_type": "sandy", "avg_rainfall": 900,  "avg_temp": 28, "farm_type": "crop",      "recommendation": "cassava"},
    {"county": "Mombasa",    "soil_type": "sandy", "avg_rainfall": 900,  "avg_temp": 28, "farm_type": "livestock",  "recommendation": "chicken"},
    {"county": "Kwale",      "soil_type": "sandy", "avg_rainfall": 900,  "avg_temp": 28, "farm_type": "crop",      "recommendation": "cassava"},
    {"county": "Kwale",      "soil_type": "sandy", "avg_rainfall": 900,  "avg_temp": 28, "farm_type": "livestock",  "recommendation": "goat"},
    {"county": "Kilifi",     "soil_type": "sandy", "avg_rainfall": 900,  "avg_temp": 30, "farm_type": "crop",      "recommendation": "cassava"},
    {"county": "Kilifi",     "soil_type": "sandy", "avg_rainfall": 900,  "avg_temp": 30, "farm_type": "livestock",  "recommendation": "chicken"},
    {"county": "Tana River", "soil_type": "sandy", "avg_rainfall": 350,  "avg_temp": 31, "farm_type": "crop",      "recommendation": "sorghum"},
    {"county": "Tana River", "soil_type": "sandy", "avg_rainfall": 350,  "avg_temp": 31, "farm_type": "livestock",  "recommendation": "camel"},
    {"county": "Lamu",       "soil_type": "sandy", "avg_rainfall": 700,  "avg_temp": 29, "farm_type": "crop",      "recommendation": "coconut"},
    {"county": "Lamu",       "soil_type": "sandy", "avg_rainfall": 700,  "avg_temp": 29, "farm_type": "livestock",  "recommendation": "goat"},
    {"county": "Taita Taveta","soil_type":"loamy",  "avg_rainfall": 750,  "avg_temp": 25, "farm_type": "crop",      "recommendation": "beans"},
    {"county": "Taita Taveta","soil_type":"loamy",  "avg_rainfall": 750,  "avg_temp": 25, "farm_type": "livestock",  "recommendation": "goat"},

    # ── North Eastern ─────────────────────────────────────────────────────────
    {"county": "Garissa",    "soil_type": "sandy", "avg_rainfall": 200,  "avg_temp": 33, "farm_type": "crop",      "recommendation": "green_grams"},
    {"county": "Garissa",    "soil_type": "sandy", "avg_rainfall": 200,  "avg_temp": 33, "farm_type": "livestock",  "recommendation": "camel"},
    {"county": "Wajir",      "soil_type": "sandy", "avg_rainfall": 200,  "avg_temp": 32, "farm_type": "crop",      "recommendation": "green_grams"},
    {"county": "Wajir",      "soil_type": "sandy", "avg_rainfall": 200,  "avg_temp": 32, "farm_type": "livestock",  "recommendation": "camel"},
    {"county": "Mandera",    "soil_type": "sandy", "avg_rainfall": 180,  "avg_temp": 34, "farm_type": "crop",      "recommendation": "green_grams"},
    {"county": "Mandera",    "soil_type": "sandy", "avg_rainfall": 180,  "avg_temp": 34, "farm_type": "livestock",  "recommendation": "camel"},

    # ── Eastern ───────────────────────────────────────────────────────────────
    {"county": "Marsabit",   "soil_type": "sandy", "avg_rainfall": 350,  "avg_temp": 22, "farm_type": "crop",      "recommendation": "sorghum"},
    {"county": "Marsabit",   "soil_type": "sandy", "avg_rainfall": 350,  "avg_temp": 22, "farm_type": "livestock",  "recommendation": "camel"},
    {"county": "Isiolo",     "soil_type": "sandy", "avg_rainfall": 300,  "avg_temp": 28, "farm_type": "crop",      "recommendation": "green_grams"},
    {"county": "Isiolo",     "soil_type": "sandy", "avg_rainfall": 300,  "avg_temp": 28, "farm_type": "livestock",  "recommendation": "goat"},
    {"county": "Meru",       "soil_type": "loamy", "avg_rainfall": 1200, "avg_temp": 20, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Meru",       "soil_type": "loamy", "avg_rainfall": 1200, "avg_temp": 20, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Tharaka-Nithi","soil_type":"loamy","avg_rainfall": 900,  "avg_temp": 22, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Tharaka-Nithi","soil_type":"loamy","avg_rainfall": 900,  "avg_temp": 22, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Embu",       "soil_type": "clay",  "avg_rainfall": 1000, "avg_temp": 21, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Embu",       "soil_type": "clay",  "avg_rainfall": 1000, "avg_temp": 21, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Kitui",      "soil_type": "sandy", "avg_rainfall": 250,  "avg_temp": 28, "farm_type": "crop",      "recommendation": "green_grams"},
    {"county": "Kitui",      "soil_type": "sandy", "avg_rainfall": 250,  "avg_temp": 28, "farm_type": "livestock",  "recommendation": "goat"},
    {"county": "Machakos",   "soil_type": "sandy", "avg_rainfall": 600,  "avg_temp": 24, "farm_type": "crop",      "recommendation": "sorghum"},
    {"county": "Machakos",   "soil_type": "sandy", "avg_rainfall": 600,  "avg_temp": 24, "farm_type": "livestock",  "recommendation": "goat"},
    {"county": "Makueni",    "soil_type": "sandy", "avg_rainfall": 350,  "avg_temp": 26, "farm_type": "crop",      "recommendation": "sorghum"},
    {"county": "Makueni",    "soil_type": "sandy", "avg_rainfall": 350,  "avg_temp": 26, "farm_type": "livestock",  "recommendation": "goat"},

    # ── Central ───────────────────────────────────────────────────────────────
    {"county": "Nyandarua",  "soil_type": "loamy", "avg_rainfall": 1100, "avg_temp": 16, "farm_type": "crop",      "recommendation": "potato"},
    {"county": "Nyandarua",  "soil_type": "loamy", "avg_rainfall": 1100, "avg_temp": 16, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Nyeri",      "soil_type": "loamy", "avg_rainfall": 1200, "avg_temp": 20, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Nyeri",      "soil_type": "loamy", "avg_rainfall": 1200, "avg_temp": 20, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Kirinyaga",  "soil_type": "loamy", "avg_rainfall": 1300, "avg_temp": 20, "farm_type": "crop",      "recommendation": "rice"},
    {"county": "Kirinyaga",  "soil_type": "loamy", "avg_rainfall": 1300, "avg_temp": 20, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Murang'a",   "soil_type": "loamy", "avg_rainfall": 1150, "avg_temp": 20, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Murang'a",   "soil_type": "loamy", "avg_rainfall": 1150, "avg_temp": 20, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Kiambu",     "soil_type": "loamy", "avg_rainfall": 1100, "avg_temp": 19, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Kiambu",     "soil_type": "loamy", "avg_rainfall": 1100, "avg_temp": 19, "farm_type": "livestock",  "recommendation": "dairy_cow"},

    # ── Rift Valley ───────────────────────────────────────────────────────────
    {"county": "Turkana",    "soil_type": "sandy", "avg_rainfall": 200,  "avg_temp": 30, "farm_type": "crop",      "recommendation": "green_grams"},
    {"county": "Turkana",    "soil_type": "sandy", "avg_rainfall": 200,  "avg_temp": 30, "farm_type": "livestock",  "recommendation": "camel"},
    {"county": "West Pokot", "soil_type": "loamy", "avg_rainfall": 700,  "avg_temp": 22, "farm_type": "crop",      "recommendation": "sorghum"},
    {"county": "West Pokot", "soil_type": "loamy", "avg_rainfall": 700,  "avg_temp": 22, "farm_type": "livestock",  "recommendation": "goat"},
    {"county": "Samburu",    "soil_type": "sandy", "avg_rainfall": 350,  "avg_temp": 25, "farm_type": "crop",      "recommendation": "sorghum"},
    {"county": "Samburu",    "soil_type": "sandy", "avg_rainfall": 350,  "avg_temp": 25, "farm_type": "livestock",  "recommendation": "camel"},
    {"county": "Trans Nzoia","soil_type": "loamy", "avg_rainfall": 1100, "avg_temp": 19, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Trans Nzoia","soil_type": "loamy", "avg_rainfall": 1100, "avg_temp": 19, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Uasin Gishu","soil_type": "loamy", "avg_rainfall": 1000, "avg_temp": 18, "farm_type": "crop",      "recommendation": "wheat"},
    {"county": "Uasin Gishu","soil_type": "loamy", "avg_rainfall": 1000, "avg_temp": 18, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Elgeyo-Marakwet","soil_type":"loamy","avg_rainfall":1100,"avg_temp": 18, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Elgeyo-Marakwet","soil_type":"loamy","avg_rainfall":1100,"avg_temp": 18, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Nandi",      "soil_type": "loamy", "avg_rainfall": 1500, "avg_temp": 18, "farm_type": "crop",      "recommendation": "tea"},
    {"county": "Nandi",      "soil_type": "loamy", "avg_rainfall": 1500, "avg_temp": 18, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Baringo",    "soil_type": "sandy", "avg_rainfall": 200,  "avg_temp": 29, "farm_type": "crop",      "recommendation": "sorghum"},
    {"county": "Baringo",    "soil_type": "sandy", "avg_rainfall": 200,  "avg_temp": 29, "farm_type": "livestock",  "recommendation": "goat"},
    {"county": "Laikipia",   "soil_type": "loamy", "avg_rainfall": 650,  "avg_temp": 20, "farm_type": "crop",      "recommendation": "beans"},
    {"county": "Laikipia",   "soil_type": "loamy", "avg_rainfall": 650,  "avg_temp": 20, "farm_type": "livestock",  "recommendation": "beef_cattle"},
    {"county": "Nakuru",     "soil_type": "loamy", "avg_rainfall": 800,  "avg_temp": 22, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Nakuru",     "soil_type": "loamy", "avg_rainfall": 800,  "avg_temp": 22, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Narok",      "soil_type": "clay",  "avg_rainfall": 700,  "avg_temp": 21, "farm_type": "crop",      "recommendation": "wheat"},
    {"county": "Narok",      "soil_type": "clay",  "avg_rainfall": 700,  "avg_temp": 21, "farm_type": "livestock",  "recommendation": "beef_cattle"},
    {"county": "Kajiado",    "soil_type": "sandy", "avg_rainfall": 450,  "avg_temp": 24, "farm_type": "crop",      "recommendation": "beans"},
    {"county": "Kajiado",    "soil_type": "sandy", "avg_rainfall": 450,  "avg_temp": 24, "farm_type": "livestock",  "recommendation": "beef_cattle"},
    {"county": "Kericho",    "soil_type": "loamy", "avg_rainfall": 1800, "avg_temp": 17, "farm_type": "crop",      "recommendation": "tea"},
    {"county": "Kericho",    "soil_type": "loamy", "avg_rainfall": 1800, "avg_temp": 17, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Bomet",      "soil_type": "loamy", "avg_rainfall": 1600, "avg_temp": 18, "farm_type": "crop",      "recommendation": "tea"},
    {"county": "Bomet",      "soil_type": "loamy", "avg_rainfall": 1600, "avg_temp": 18, "farm_type": "livestock",  "recommendation": "dairy_cow"},

    # ── Western ───────────────────────────────────────────────────────────────
    {"county": "Kakamega",   "soil_type": "loamy", "avg_rainfall": 2000, "avg_temp": 22, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Kakamega",   "soil_type": "loamy", "avg_rainfall": 2000, "avg_temp": 22, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Vihiga",     "soil_type": "loamy", "avg_rainfall": 1800, "avg_temp": 21, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Vihiga",     "soil_type": "loamy", "avg_rainfall": 1800, "avg_temp": 21, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Bungoma",    "soil_type": "loamy", "avg_rainfall": 1500, "avg_temp": 21, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Bungoma",    "soil_type": "loamy", "avg_rainfall": 1500, "avg_temp": 21, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Busia",      "soil_type": "clay",  "avg_rainfall": 1400, "avg_temp": 23, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Busia",      "soil_type": "clay",  "avg_rainfall": 1400, "avg_temp": 23, "farm_type": "livestock",  "recommendation": "chicken"},

    # ── Nyanza ────────────────────────────────────────────────────────────────
    {"county": "Siaya",      "soil_type": "clay",  "avg_rainfall": 1200, "avg_temp": 24, "farm_type": "crop",      "recommendation": "sorghum"},
    {"county": "Siaya",      "soil_type": "clay",  "avg_rainfall": 1200, "avg_temp": 24, "farm_type": "livestock",  "recommendation": "fish_farming"},
    {"county": "Kisumu",     "soil_type": "clay",  "avg_rainfall": 1100, "avg_temp": 25, "farm_type": "crop",      "recommendation": "rice"},
    {"county": "Kisumu",     "soil_type": "clay",  "avg_rainfall": 1100, "avg_temp": 25, "farm_type": "livestock",  "recommendation": "fish_farming"},
    {"county": "Homa Bay",   "soil_type": "clay",  "avg_rainfall": 1000, "avg_temp": 26, "farm_type": "crop",      "recommendation": "sorghum"},
    {"county": "Homa Bay",   "soil_type": "clay",  "avg_rainfall": 1000, "avg_temp": 26, "farm_type": "livestock",  "recommendation": "fish_farming"},
    {"county": "Migori",     "soil_type": "loamy", "avg_rainfall": 1300, "avg_temp": 23, "farm_type": "crop",      "recommendation": "maize"},
    {"county": "Migori",     "soil_type": "loamy", "avg_rainfall": 1300, "avg_temp": 23, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Kisii",      "soil_type": "loamy", "avg_rainfall": 1800, "avg_temp": 19, "farm_type": "crop",      "recommendation": "tea"},
    {"county": "Kisii",      "soil_type": "loamy", "avg_rainfall": 1800, "avg_temp": 19, "farm_type": "livestock",  "recommendation": "dairy_cow"},
    {"county": "Nyamira",    "soil_type": "loamy", "avg_rainfall": 1900, "avg_temp": 18, "farm_type": "crop",      "recommendation": "tea"},
    {"county": "Nyamira",    "soil_type": "loamy", "avg_rainfall": 1900, "avg_temp": 18, "farm_type": "livestock",  "recommendation": "dairy_cow"},

    # ── Nairobi ───────────────────────────────────────────────────────────────
    {"county": "Nairobi",    "soil_type": "loamy", "avg_rainfall": 850,  "avg_temp": 18, "farm_type": "crop",      "recommendation": "beans"},
    {"county": "Nairobi",    "soil_type": "loamy", "avg_rainfall": 850,  "avg_temp": 18, "farm_type": "livestock",  "recommendation": "chicken"},
]
