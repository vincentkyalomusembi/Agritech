# 🌾 Agritech AI — Intelligence-Driven Farming Assistant

> *An AI-powered agricultural advisory system accessible via USSD, combining satellite data, weather APIs, LLM guidance, and real market prices to help farmers make better crop & livestock decisions.*

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack by Component](#technology-stack-by-component)
3. [System Architecture](#system-architecture)
4. [Component Breakdown](#component-breakdown)
5. [Detailed Project Workflow](#detailed-project-workflow)
6. [Setup & Configuration](#setup--configuration)
7. [Testing Guide](#testing-guide)
8. [Deployment](#deployment)
9. [API Reference](#api-reference)
10. [Troubleshooting](#troubleshooting)

---

## System Overview

### What is Agritech AI?

Agritech AI is a **USSD-based decision support system** that helps Kenyan farmers answer three key questions:

1. **What should I plant?** (Crop recommendations based on region, weather, soil, experience, budget)
2. **What livestock should I raise?** (Livestock recommendations tailored to climate and resources)
3. **What's my farm's current status?** (Weather alerts, disease risks, market prices, expert contacts)

### Key Features

✅ **Satellite-Powered Insights** - Uses Google Earth Engine (MODIS, CHIRPS) to analyze NDVI, rainfall, and drought conditions
✅ **Live Weather Context** - Integrates OpenWeather API for temperature, humidity, wind, and precipitation
✅ **Real Market Prices** - FAO Food Price Index with GEE-driven adjustments for scarcity premiums
✅ **AI-Generated Advice** - Google Gemini LLM creates farmer-friendly explanations
✅ **Multi-Option Recommendations** - Shows primary + 3 alternative crops/livestock with rankings
✅ **Subscription-Gated Alerts** - Weather and disease alerts for subscribed users only
✅ **USSD-First Design** - Accessible to feature phones; no smartphone required
✅ **Production-Ready** - Runs on FastAPI + Render with Docker containerization

---

## Technology Stack by Component

### **Core Framework**
- **FastAPI** (Python) — Web server handling USSD requests, HTTP endpoints
- **Python 3.11** — Runtime environment
- **Uvicorn** — ASGI server for FastAPI

### **Data Sources & APIs**

| Service | Purpose | Technology | Data |
|---------|---------|-----------|------|
| **Google Earth Engine** | Satellite crop analysis | `ee` (earthengine-api) | MODIS NDVI, CHIRPS rainfall |
| **OpenWeather** | Live weather context | REST API | Temperature, humidity, wind, clouds |
| **Google Gemini** | AI advice generation | `google.generativeai` | LLM-based explanation text |
| **FAO Food Price Index** | Market price data | REST API + caching | Commodity prices (KES) with GEE adjustments |
| **Africa's Talking** | USSD gateway | REST API | SMS + USSD callback handling |

### **Database & Storage**
- **JSON files** (local) — User profiles, GEE cache, price cache
- **In-memory** — Session state during USSD flow
- **Render** (production) — Persistent storage via environment variables

### **Deployment**
- **Docker** — Containerization for Render
- **Render** — Cloud hosting (production)
- **ngrok** — Public tunnel for local development/testing

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Farmer (USSD Phone)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ SMS *123# → Africa's Talking
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Africa's Talking USSD Gateway (Callback)            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ POST /ussd (text, phoneNumber)
                     ▼
        ┌────────────────────────────────┐
        │      FastAPI App (app.py)      │
        │  - Route: /ussd handler        │
        │  - Session state: USSD flow    │
        └────┬─────────────────────┬─────┘
             │                     │
       ┌─────▼──────┐    ┌────────▼──────────┐
       │  ussd_flow │    │  recommender.py   │
       │   - Menu   │    │  - Context merge  │
       │ - Options  │    │ - Multi-options   │
       └─────┬──────┘    └────────┬──────────┘
             │                    │
             │         ┌──────────┼──────────┐
             │         │          │          │
             │    ┌────▼────┐ ┌──▼────┐ ┌──▼──────┐
             │    │   GEE   │ │Weather│ │  FAO   │
             │    │ Satellite│ │ API  │ │ Prices │
             │    │ Analysis │ │      │ │ + Cache│
             │    └────┬────┘ └──┬────┘ └──┬─────┘
             │         │        │         │
             │    ┌────────────────────────▼──┐
             │    │   services/advisory.py    │
             │    │  (Gemini LLM Integration) │
             │    └────────┬─────────────────┘
             │             │
        ┌────▼─────────────▼────────────┐
        │    USSD Response Formatter     │
        │  - Primary recommendation     │
        │  - Alternative options        │
        │  - Weather summary            │
        │  - AI advice (first 100 chars)│
        └────┬─────────────────────────┘
             │
             │ Response (plain text)
             ▼
        Africa's Talking → Farmer's Phone
```

---

## Component Breakdown

### 1. **Google Earth Engine (GEE)** - Satellite Analysis
**File:** `services/gee.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Analyze vegetation and rainfall patterns at county level |
| **Technology** | Google Earth Engine Python API (`ee` library) |
| **Datasets Used** | MODIS/061/MOD13Q1 (NDVI), UCSB-CHG/CHIRPS/DAILY (rainfall) |
| **Key Metrics** | NDVI, 30-day rainfall total, rainfall anomaly % |
| **Output** | Alert level (low/medium/high), insights dict |
| **Caching** | `data/gee_alerts_latest.json` (24hr refresh via script) |
| **Why GEE?** | Free, global, high-resolution satellite data (250m MODIS, 5km CHIRPS) |

**How It Works:**
1. Initialize with service account credentials (`GEE_SERVICE_ACCOUNT`, `GEE_KEY_PATH`, `GEE_PROJECT_ID`)
2. Define county geometries as lat/lon bounding boxes
3. Filter MODIS for last 30 days → compute mean NDVI
4. Filter CHIRPS for last 30 days → sum rainfall
5. Compare against 365-day baseline → anomaly %
6. Derive alert level: NDVI <0.2 OR anomaly <-40% = HIGH risk
7. Return to recommender for crop adjustment

**Key Insight:** *GEE is "heavy lifting" — computed once/day, cached for fast USSD responses*

---

### 2. **OpenWeather API** - Live Weather Context
**File:** `services/weather.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Get real-time local weather for farm decision-making |
| **Technology** | OpenWeather REST API (free tier: 5-day forecast, current) |
| **Data Fetched** | Temperature, feels-like, humidity, pressure, wind, clouds, condition |
| **Update Frequency** | Every API call (avg 50ms latency) |
| **Fallback** | Deterministic mock if API key missing or request fails |
| **Why OpenWeather?** | Free tier sufficient, low latency, predictable JSON |

**How It Works:**
1. farmer enters county in USSD
2. `get_weather(county)` is called
3. If API key exists → call OpenWeather for coordinates
4. If not → use mock data (based on county hash, deterministic)
5. Parse response → extract all 7 fields
6. Return to recommender & advisory

**Key Insight:** *Weather is "contextual" — used to validate GEE signals (e.g., "high temp + high NDVI = good"; "high temp + low NDVI = stress")*

---

### 3. **FAO Food Price Index** - Real Market Prices
**File:** `services/fao_prices.py` + `services/market.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Provide farmers with current commodity market prices |
| **Technology** | FAO FAOSTAT public data + local caching |
| **Prices Covered** | 10 commodities: maize, beans, sorghum, millet, cassava, goat, sheep, chicken, dairy, fish |
| **Price Range** | Min/max based on FAO regional averages (converted to KES) |
| **Cache** | `data/fao_prices_cache.json` (24-hour TTL) |
| **Adjustments** | GEE-driven: High drought = +20%, Low risk = -5% |
| **Why FAO?** | Authoritative, global, free, monthly updates |

**How It Works:**
1. When farmer selects market prices (Option 5)
2. `get_market_prices(commodity, county, gee_adjust)` is called
3. Load FAO cache or fetch fresh if expired
4. Optional: Adjust prices by GEE risk level
5. Return min/max range + unit

**Example Price Impact:**
```
Base maize: 2600-3500 KES/bag (FAO)
High drought (GEE): ×1.2 → 3120-4200 KES/bag (+20% premium)
Abundant harvest (GEE): ×0.95 → 2470-3325 KES/bag (-5% discount)
```

**Key Insight:** *Farmers see prices that reflect *their local conditions*, not global averages*

---

### 4. **Google Gemini LLM** - AI Advice Generation
**File:** `services/advisory.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Generate farmer-friendly explanations for recommendations |
| **Technology** | Google Generative AI (Gemini 2.5-flash) |
| **Prompt Strategy** | Structured input: county, GEE risk, weather, farm inputs, alternatives |
| **Output** | 1-3 sentence plaintext explanation |
| **Fallback** | Template-based advice if API fails or no key |
| **Why Gemini?** | Fast (flash model), free tier, natural language quality |

**How It Works:**
1. `build_advice(county, farm_type, soil, size, budget, exp, options, gee_insights, weather)`
2. Construct prompt: *"You are a Kenyan agriculture expert..."*
   - Include GEE risk as primary signal
   - Include weather as secondary context
   - Include farm constraints (size, budget, experience)
   - Ask for irrigation/disease/heat-stress advice
3. Call Gemini API → receive text response
4. Return first 100 chars for USSD (short messages)
5. Fallback to template if error

**Sample Prompt:**
```
"Farmer in {county}, {farm_type}, {experience_level} experience.
GEE shows NDVI={ndvi} (high drought risk).
Weather: {temp}°C, {humidity}% humidity, {wind} m/s wind.
Farm: {size} hectares, {budget} KES budget.
Recommend from {options} and explain why. 
Mention irrigation, disease, or heat-stress if relevant. 
Answer in 1-2 farmer-friendly sentences."
```

**Key Insight:** *Gemini validates and contextualizes all upstream data (GEE, weather, market) into actionable advice*

---

### 5. **USSD Flow Manager** - User Interaction State Machine
**File:** `ussd_flow.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Manage 9-option menu + multi-step recommendation flows |
| **Technology** | State machine (based on `*` delimited input) |
| **Menu Options** | 1=Crop, 2=Livestock, 3=Weather, 4=Disease, 5=Prices, 6=Expert, 7=Tips, 8=Profile, 9=Subscribe |
| **Session Handling** | Stateless (input encoded in USSD text string) |
| **Response Format** | CON (continue) or END (terminate) |
| **Why USSD?** | Works on any phone; SMS/cellular only; no internet required from user |

**How It Works:**

**Option 1-2 (Crop/Livestock Recommendation):**
```
User: "1"
→ System: "CON Enter county"
User: "1*Makueni"
→ System: "CON Enter soil type"
User: "1*Makueni*sandy"
→ System: "CON Enter farm size"
...
User: "1*Makueni*sandy*2*50000*3"
→ System: [Call recommender] → END response with recommendation + options + advice
```

**Option 3-4 (Alerts) with Auto-Fill:**
```
If user has county in saved profile:
  User: "3"
  → System: [Auto-detect county from profile] → END weather alert
  
If user has no profile:
  User: "3"
  → System: "CON Enter your county"
  User: "3*Makueni"
  → System: END [Weather alert for Makueni]
```

**Option 5 (Market Prices):**
```
User: "5"
→ System: "CON Select commodity: 1. Maize 2. Beans ... 10. Fish"
User: "5*1"
→ System: END "Market Prices - Maize: KES 2600-3500/bag"
```

**Option 7 (Seasonal Tips):**
```
Current month = May (rainy season)
User farm_type = crop
→ Crop Tips (Rainy Season): Prepare land, use quality seeds, manage drainage, etc.
```

**Option 8 (Profile Edit):**
```
User: "8"
→ System: "CON Show current profile, select field to edit (1-4)"
User: "8*1"
→ System: "CON Enter your new name"
User: "8*1*John Farmer"
→ System: END "Name updated successfully"
```

**Key Insight:** *USSD state encoded in text input → no server-side session store needed → truly stateless*

---

### 6. **Recommendation Engine** - Decision Logic
**File:** `recommender.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Synthesize all inputs (GEE, weather, farm data) into top crop/livestock options |
| **Technology** | Rule-based ranking (not ML) + heuristic adjustments |
| **Inputs** | County, farm type, soil, size, budget, experience, weather, GEE risk |
| **Output** | Primary recommendation + ranked list of 3 alternatives |
| **Logic** | GEE drives primary choice; weather fine-tunes ranking |
| **Why Rules?** | Interpretable, fast, no training data needed |

**How It Works:**

1. **Load base options:**
   - Crops: sorghum, millet, cowpea, cassava, beans, maize
   - Livestock: goat, sheep, chicken, dairy cattle

2. **Apply GEE adjustments:**
   - High drought (NDVI <0.2 OR anomaly <-40%) → shift to drought-tolerant (sorghum, millet, goat)
   - Medium drought → shift slightly
   - Low risk → keep original list

3. **Apply weather adjustments:**
   - High temp (≥30°C) + high humidity → beans, maize
   - High temp + low humidity (drought) → sorghum, millet, goat
   - High humidity (≥75%) for livestock → dairy cattle (water-loving)

4. **Rank by farm constraints:**
   - Budget < 10k KES → chicken (cheaper to raise)
   - Budget > 50k KES → dairy/goat (higher investment)
   - Experience = beginner → maize (safest crop)
   - Experience = expert → sorghum (more complex)

5. **Select top 4 → return as {recommendation, recommendation_options}**

**Example:**
```
Input: Makueni (high drought), 2 acres, 30k budget, beginner, current weather 32°C/40% humidity
GEE: High risk → prefer sorghum
Weather: High heat + low humidity → prefer sorghum
Budget: 30k → can afford goat × 10
Experience: Beginner → prefer proven crops

Output:
  recommendation: "sorghum"
  recommendation_options: ["millet", "cowpea", "cassava"]
  
  (For livestock: 
    recommendation: "goat"
    recommendation_options: ["sheep", "chicken", "dairy cattle"]
  )
```

**Key Insight:** *Rules are transparent (farmer can ask "why sorghum?") and fast (<100ms)*

---

### 7. **Alert System** - Weather & Disease Risk
**File:** `services/alerts.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Alert subscribed users to weather & disease risks with GEE + live weather context |
| **Technology** | GEE alerts + OpenWeather current conditions |
| **Gating** | Subscription required (Option 9 to subscribe) |
| **Frequency** | On-demand via USSD (no push notifications yet) |
| **Data Used** | GEE risk level, NDVI, rainfall anomaly, real OpenWeather conditions |
| **Why Both GEE & OpenWeather?** | GEE shows long-term trends; OpenWeather shows immediate conditions |

**How It Works:**

**Weather Alert:**
```
build_weather_alert(county, subscribed):
  GEE: alert_level, NDVI, rainfall_anomaly
  OpenWeather: condition, temp, feels_like, humidity, wind, clouds
  
  Output:
  "Weather in Makueni: light rain, 18°C
   Alert: HIGH drought (NDVI=0.54, anomaly=-100%)
   Live: 95% humidity, 2 m/s wind, scattered clouds"
```

**Disease Alert:**
```
build_disease_alert(county, subscribed):
  GEE: rainfall_anomaly, high_rainfall = fungal disease risk
  OpenWeather: temp, humidity
  
  Rules:
    - High humidity (≥80%) + temp 20-28°C = fungal disease HIGH
    - High temp (≥30°C) = pest/stress HIGH
    - Low rainfall (anomaly <-30%) = crop stress HIGH
  
  Output:
  "Disease Alert in Makueni: HIGH risk
   Fungal disease likely (high humidity 95%)
   Action: Monitor for leaf spots, consider fungicide spray"
```

**Key Insight:** *Alerts are actionable → not just "risk is high" but "because humidity is 95%, watch for fungal disease"*

---

### 8. **User Store** - Profile Management
**File:** `user_store.py`

| Aspect | Details |
|--------|---------|
| **Purpose** | Persist user profiles (name, county, farm type, subscription) |
| **Technology** | In-memory list + JSON file (no true database yet) |
| **Data Stored** | phone_number, name, county, farm_type, soil_type, subscribed, subscription_plan |
| **Persistence** | Session-based (reset on app restart); can be extended to file/DB |
| **Why In-Memory?** | Simple, no dependencies, sufficient for demo |

**How It Works:**
1. Demo users hardcoded (Vin Demo, Amina Demo, etc.)
2. `get_user_by_phone(phone)` → returns user dict or None
3. `update_user(phone, {updates})` → modifies user dict
4. `subscribe_user(phone, plan)` → sets subscribed=True
5. All subsequent calls use this data (county auto-fill, farm type for tips, etc.)

---

---

## Detailed Project Workflow

### End-to-End Flow: From USSD Dial to Recommendation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 1: Farmer dials *123#                                                 │
│ ─────────────────────────────────────────────────────────────────────────   │
│ • Farmer on feature phone sends USSD request                              │
│ • Africa's Talking gateway receives SMS                                    │
│ • HTTP POST to FastAPI: POST /ussd?text=&phoneNumber=+254792246733       │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│ Step 2: FastAPI routes to handler                                          │
│ ─────────────────────────────────────────────────────────────────────────   │
│ • app.py receives POST /ussd                                              │
│ • Extracts text (empty) and phoneNumber                                   │
│ • Calls handle_ussd(text="", phone_number="+254792246733")               │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│ Step 3: Show main menu                                                     │
│ ─────────────────────────────────────────────────────────────────────────   │
│ ussd_flow.handle_ussd() calls _main_menu("Vin Demo")                      │
│ Returns: CON Welcome Vin Demo in Agritech AI                              │
│          1. Crop Recommendation                                            │
│          2. Livestock Recommendation                                       │
│          ...                                                                │
│          9. Subscribe                                                       │
│                                                                             │
│ Response sent back to Africa's Talking → Farmer's phone                   │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│ Step 4: Farmer replies "1" (Crop Recommendation)                           │
│ ─────────────────────────────────────────────────────────────────────────   │
│ handle_ussd(text="1", phone_number="+254792246733")                       │
│ parts = ["1"] (len=1)                                                     │
│ Response: CON Enter your county (e.g., Makueni):                          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│ Step 5: Farmer replies "1*Makueni"                                         │
│ ─────────────────────────────────────────────────────────────────────────   │
│ parts = ["1", "Makueni"] (len=2)                                          │
│ Response: CON Enter soil type (loamy/sandy/clay) or type 'unknown':       │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
              [Steps 6-7: Collect farm size & budget]
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│ Step 8: All data collected "1*Makueni*sandy*2*50000*1"                     │
│ ─────────────────────────────────────────────────────────────────────────   │
│ parts = ["1", "Makueni", "sandy", "2", "50000", "1"] (len=6)             │
│ Call get_recommendation(county="Makueni", farm_type="crop", ...)          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│ Step 9: Recommendation Engine runs                                         │
│ ─────────────────────────────────────────────────────────────────────────   │
│ recommender.py:                                                            │
│   1. Load mock farm data (from seed_data.csv)                             │
│   2. Fetch GEE insights:                                                  │
│      - Load from cache (data/gee_alerts_latest.json)                      │
│      - If missing, compute live via services/gee.py                       │
│      - For Makueni: alert_level=HIGH, NDVI=0.54, anomaly=-100%          │
│   3. Fetch weather via OpenWeather:                                       │
│      - For Makueni: temp=18°C, humidity=95%, wind=2 m/s                 │
│   4. Fetch FAO prices:                                                    │
│      - Load cache (data/fao_prices_cache.json)                            │
│      - Adjust by GEE risk: high drought → +20%                           │
│   5. Call _adjust_recommendation_by_context():                            │
│      - GEE high risk + low humidity drought → shift to sorghum/millet    │
│      - Weather: 18°C is cool, 95% humidity is high                       │
│      - Budget 50k is decent, beginner = prefer safe crops                │
│   6. Primary recommendation: SORGHUM                                       │
│   7. Alternatives: [MILLET, COWPEA, CASSAVA]                             │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│ Step 10: Gemini LLM generates advice                                       │
│ ─────────────────────────────────────────────────────────────────────────   │
│ services/advisory.py calls build_advice():                                 │
│   Prompt: "Farmer in Makueni, crop, beginner. GEE NDVI=0.54 (HIGH drought)│
│             Temp 18°C, humidity 95%. Budget 50k. Recommend from            │
│             [sorghum, millet, cowpea, cassava]. Mention irrigation,       │
│             disease, heat stress."                                         │
│                                                                             │
│   Gemini Returns:                                                          │
│   "Sorghum is drought-tolerant and needs less water than maize in dry     │
│    periods. Your high humidity risks fungal disease—practice crop rotation │
│    and plant in wider rows for air circulation."                          │
│                                                                             │
│   Truncate to 100 chars for USSD: "Sorghum is drought-tolerant and needs │
│                                    less water..."                          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│ Step 11: Format USSD Response                                              │
│ ─────────────────────────────────────────────────────────────────────────   │
│ ussd_flow._format_weather_summary(): Weather: light rain | Temp: 18°C    │
│ ussd_flow._format_options():         Options: Millet, Cowpea, Cassava    │
│                                                                             │
│ Final response:                                                             │
│ END Recommended for Makueni:                                              │
│ • Sorghum                                                                  │
│ • Options: Millet, Cowpea, Cassava                                        │
│ • Weather: light rain | Temp: 18°C | Humidity: 95% | Wind: 2 m/s        │
│ Advice: Sorghum is drought-tolerant and needs less water...              │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│ Step 12: Response sent to farmer                                           │
│ ─────────────────────────────────────────────────────────────────────────   │
│ FastAPI returns plain text to Africa's Talking                            │
│ Africa's Talking delivers SMS to +254792246733                            │
│ Farmer reads on their phone screen                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Setup & Configuration

### Prerequisites
- Python 3.11+
- Virtual environment (venv or conda)
- Internet (for GEE, OpenWeather, FAO APIs)

### Environment Variables
Create a `.env` file in the project root:

```bash
# Google Earth Engine
GEE_PROJECT_ID=agritech-495121
GEE_SERVICE_ACCOUNT=agritech@agritech-495121.iam.gserviceaccount.com
GEE_KEY_PATH=/path/to/service-account-key.json

# OpenWeather API
OPENWEATHER_KEY=your-openweather-api-key

# Google Gemini
GEMINI_API_KEY=your-gemini-api-key

# Africa's Talking
AT_APIKEY=your-africas-talking-api-key
AT_USERNAME=your-username
```

### Installation

```bash
cd /home/vin/Desktop/Agritech

# Create virtual environment
python3.11 -m venv env
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize GEE credentials
python -c "from services.gee import init_gee; print(init_gee())"
```

### Directory Structure

```
Agritech/
├── app.py                    # FastAPI server + endpoints
├── recommender.py           # Recommendation engine (crop/livestock)
├── ussd_flow.py             # USSD state machine + menu handling
├── user_store.py            # User profiles + subscriptions
├── services/
│   ├── gee.py              # Google Earth Engine (satellite analysis)
│   ├── weather.py          # OpenWeather API integration
│   ├── fao_prices.py       # FAO price data + caching
│   ├── market.py           # Market price endpoint
│   ├── advisory.py         # Gemini LLM integration
│   ├── alerts.py           # Weather & disease alerts
│   └── africastalking.py   # Africa's Talking SMS
├── data/
│   ├── gee_alerts_latest.json  # GEE cache (updated daily)
│   ├── fao_prices_cache.json   # FAO price cache (24hr TTL)
│   └── users.json              # User profiles (optional)
├── scripts/
│   ├── update_gee_summaries.py # Daily GEE cache refresh
│   ├── start.sh                # Dev server startup
│   └── stop.sh                 # Cleanup script
├── docs/images/            # Placeholder for workflow diagrams
├── .env                    # Environment variables (DO NOT COMMIT)
├── .dockerignore
├── Dockerfile              # Production containerization
├── render.yaml             # Render deployment config
├── README.md              # This file
└── requirements.txt       # Python dependencies
```

---

## Testing Guide

### Test 1: Local USSD Flow (Stateless)

```bash
python -c "
import sys
sys.path.insert(0, '/home/vin/Desktop/Agritech')
from ussd_flow import handle_ussd

# Step 1: Main menu
response = handle_ussd('', phone_number='+254792246733')
print('Main menu:', response[:50])

# Step 2: Start crop recommendation
response = handle_ussd('1', phone_number='+254792246733')
print('Ask county:', response[:50])

# Step 3: Full flow
response = handle_ussd('1*Makueni*sandy*2*50000*1', phone_number='+254792246733')
print('Recommendation:', response[:100])
"
```

### Test 2: GEE Data Fetch

```bash
python -c "
import sys
sys.path.insert(0, '/home/vin/Desktop/Agritech')
from services.gee import get_gee_insights

# Fetch for Makueni
result = get_gee_insights('Makueni')
print(f'Status: {result[\"status\"]}')
print(f'Alert level: {result[\"alert_level\"]}')
print(f'NDVI: {result[\"metrics\"][\"ndvi\"]}')
"
```

### Test 3: Weather + Advice

```bash
python -c "
import sys
sys.path.insert(0, '/home/vin/Desktop/Agritech')
from services.weather import get_weather
from services.advisory import build_advice

weather = get_weather('Makueni')
print('Weather:', weather)

advice = build_advice(
    county='Makueni',
    farm_type='crop',
    soil='sandy',
    farm_size='2 acres',
    budget='50000 KES',
    experience='beginner',
    recommendation_options=['sorghum', 'millet', 'cowpea'],
    gee_insights={'alert_level': 'high', 'metrics': {'ndvi': 0.54}},
    weather=weather
)
print('Advice:', advice[:150])
"
```

### Test 4: Market Prices with GEE Adjustment

```bash
python -c "
import sys
sys.path.insert(0, '/home/vin/Desktop/Agritech')
from services.market import get_market_prices

# Without adjustment
price = get_market_prices('maize', gee_adjust=False)
print(f'Maize base: {price[\"min\"]}-{price[\"max\"]}')

# With adjustment (high drought)
price = get_market_prices('maize', county='Makueni', gee_adjust=True)
print(f'Maize (high drought): {price[\"min\"]}-{price[\"max\"]}')
"
```

### Test 5: Full Recommendation Flow

```bash
python -c "
import sys
sys.path.insert(0, '/home/vin/Desktop/Agritech')
from recommender import get_recommendation

rec = get_recommendation(
    county='Makueni',
    farm_type='crop',
    soil='sandy',
    farm_size='2 acres',
    budget='50000 KES',
    experience='beginner'
)

print('Recommendation:', rec['recommendation'])
print('Options:', rec['recommendation_options'])
print('Advice:', rec['advice'][:100])
"
```

---

## Deployment

### Local Development

```bash
# Start FastAPI + ngrok
bash start.sh

# Server runs on http://localhost:8000
# Public URL: https://<ngrok-id>.ngrok.io/ussd
# Use this URL in Africa's Talking USSD callback settings
```

### Production (Render)

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Agritech AI: Production ready"
   git push -u origin main
   ```

2. **Create Render Service**
   - Connect GitHub repo
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - Environment variables: Set all `.env` vars in Render dashboard

3. **Update Africa's Talking Callback**
   - Old: `https://<ngrok-id>.ngrok.io/ussd`
   - New: `https://your-app.onrender.com/ussd`

---

## API Reference

### USSD Endpoint
```
POST /ussd
Content-Type: application/x-www-form-urlencoded

text=1*Makueni*sandy*2*50000*1
phoneNumber=+254792246733
```

### Recommendation Endpoint
```
POST /recommend
Content-Type: application/json

{
  "county": "Makueni",
  "farm_type": "crop",
  "soil": "sandy",
  "farm_size": "2 acres",
  "budget": "50000 KES",
  "experience": "beginner"
}
```

### GEE Insights Endpoint
```
GET /gee/alerts/{county}

Example: GET /gee/alerts/Makueni
Response: { "status": "ok", "alert_level": "high", "metrics": {...} }
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| GEE initialization fails | Missing credentials or service account lacks permissions | Ensure `GEE_KEY_PATH` exists and service account has `Viewer` + `Service Usage` roles |
| Weather returns mock data | OpenWeather API key missing or invalid | Check `OPENWEATHER_KEY` in `.env` |
| Gemini advice is template text | API key missing or quota exceeded | Check `GEMINI_API_KEY`; FAO prices don't depend on it |
| Prices show as 0 | FAO cache missing + API fetch failed | Run `python -c "from services.fao_prices import get_fao_prices; print(get_fao_prices())"` to repopulate |
| USSD doesn't respond | FastAPI not running or ngrok tunnel expired | Check `http://localhost:8000/health` and restart ngrok via `bash start.sh` |
| African's Talking callback fails | Callback URL incorrect or firewall issue | Verify URL matches Africa's Talking dashboard; test with `curl` |

---

## Summary

| Component | Tech | Purpose | Data Source |
|-----------|------|---------|-------------|
| **GEE** | Earth Engine API | Crop stress analysis | MODIS/CHIRPS satellites |
| **Weather** | OpenWeather | Live conditions | OpenWeather API |
| **Gemini** | LLM | Natural advice | Google Generative AI |
| **FAO Prices** | Price data + caching | Market context | FAO FAOSTAT + cache |
| **USSD Flow** | State machine | User interaction | User input (USSD) |
| **Recommender** | Rules engine | Decision synthesis | All above + farm data |
| **Alerts** | GEE + Weather | Risk notification | GEE + OpenWeather |

**The system works by:**
1. Accepting USSD inputs from farmers (text-based, no smartphone required)
2. Collecting context (county, soil, farm size, budget, experience)
3. Fetching satellite data (GEE), live weather (OpenWeather), and market prices (FAO)
4. Running decision logic (recommender.py) to rank crops/livestock by suitability
5. Using Gemini to explain "why" in farmer-friendly language
6. Returning compact, actionable USSD response

**All components integrate to answer the fundamental question: "What should I do on my farm, right now, and why?"**

---

**Ready to test? Run:** `python -c "from services.gee import init_gee; print(init_gee())"` to verify setup.
