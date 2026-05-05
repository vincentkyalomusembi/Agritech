# 🌾 Agritech AI — USSD-Powered Agricultural Advisory

> **AI-driven farming decisions, one USSD dial away. No smartphone required.**

Agritech combines **satellite data (GEE), live weather (OpenWeather), AI reasoning (Gemini), and real market prices (FAO)** to help Kenyan farmers make better crop and livestock decisions.

---

## 🚀 Quick Start

### Setup (2 minutes)

```bash
cd /home/vin/Desktop/Agritech
python3.11 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

### Start the server

```bash
bash start.sh
# Server: http://localhost:8000
# Public URL: https://<ngrok-id>.ngrok-free.dev/ussd
```

### Test a recommendation

```bash
python -c "from ussd_flow import handle_ussd; print(handle_ussd('1*Makueni*sandy*2*50000*1', '+254792246733'))"
```

---

## 📖 System Overview

### What the System Does

1. **Crop/Livestock Recommendations** — Based on region, soil, weather, farm size, budget, and experience
2. **Weather & Disease Alerts** — Subscription-based notifications with GEE + live conditions
3. **Market Prices** — Real FAO prices adjusted for local drought conditions
4. **Advisory Tips** — Seasonal, farm-type specific guidance from Gemini LLM
5. **Expert Contacts** — Veterinarians and agricultural officers by county
6. **User Profiles** — Editable by farmers, enables county auto-fill

### How It Works

```
Farmer dials *123#
          ↓
    FastAPI receives USSD
          ↓
    Fetches GEE (satellite), OpenWeather, FAO prices
          ↓
    Runs recommendation engine (rule-based ranking)
          ↓
    Gemini LLM generates explanation
          ↓
    Returns compact USSD response
```

---

## 🛠 Technology Stack by Component

### Core Server
- **FastAPI** — Web framework for USSD + HTTP endpoints
- **Uvicorn** — ASGI server
- **Python 3.11** — Runtime

### Data Sources
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **GEE** | Google Earth Engine API | Satellite NDVI + rainfall analysis |
| **Weather** | OpenWeather API | Live temperature, humidity, wind, clouds |
| **Advice** | Google Gemini LLM | Human-readable explanations |
| **Prices** | FAO FAOSTAT + local cache | 10 commodities, GEE-adjusted |
| **USSD** | Africa's Talking | SMS-based user interaction |

### Storage
- **JSON files** (local) — User profiles, GEE cache, price cache
- **In-memory** — Session state during USSD flow

### Deployment
- **Docker** — Containerization
- **Render** — Cloud hosting (production)
- **ngrok** — Public tunnel (development)

---

## 📂 Project Structure

```
Agritech/
├── app.py                    # FastAPI app + /ussd endpoint
├── ussd_flow.py             # USSD menu state machine (9 options)
├── recommender.py           # Decision engine (GEE + weather + farm data)
├── user_store.py            # User profiles & subscriptions
├── services/
│   ├── gee.py              # Google Earth Engine (NDVI, rainfall, alerts)
│   ├── weather.py          # OpenWeather API
│   ├── fao_prices.py       # FAO prices + GEE adjustments
│   ├── market.py           # Market price endpoint
│   ├── advisory.py         # Gemini LLM for advice
│   ├── alerts.py           # Weather & disease alerts
│   └── africastalking.py   # Africa's Talking SMS
├── data/
│   ├── gee_alerts_latest.json   # GEE cache (daily refresh)
│   └── fao_prices_cache.json    # Price cache (24-hour TTL)
├── scripts/
│   ├── update_gee_summaries.py  # Daily GEE refresh
│   ├── start.sh                 # Dev startup
│   └── stop.sh                  # Cleanup
├── docs/images/            # Workflow diagrams (placeholder)
├── .env                    # Environment variables (see .env.example)
├── Dockerfile
├── render.yaml
├── requirements.txt
└── README.md              # This file
```

---

## 🌐 USSD Menu (9 Options)

```
Welcome Farmer!
1. Crop Recommendation
2. Livestock Recommendation
3. Weather Alerts (subscribed only)
4. Disease Alerts (subscribed only)
5. Market Prices
6. Request Expert Visit
7. Advisory Tips (seasonal)
8. My Profile (view/edit)
9. Subscribe (weekly alerts)
```

### Example Flow: Crop Recommendation (Option 1)

```
User: 1                           [Start crop recommendation]
→ System: "Enter county"

User: 1*Makueni                   [Makueni county]
→ System: "Enter soil type"

User: 1*Makueni*sandy             [Sandy soil]
→ System: "Enter farm size"

User: 1*Makueni*sandy*2           [2 acres]
→ System: "Enter budget (KES)"

User: 1*Makueni*sandy*2*50000     [50k budget]
→ System: "Select experience"

User: 1*Makueni*sandy*2*50000*1   [Beginner]
→ System: 
   END Recommended for Makueni:
   • Sorghum
   • Options: Millet, Cowpea, Cassava
   • Weather: light rain | Temp: 18°C | Humidity: 95%
   Advice: Sorghum is drought-tolerant and needs less water...
```

---

## 🔧 Environment Variables

Create a `.env` file in the project root:

```bash
# Google Earth Engine credentials
GEE_PROJECT_ID=your-gcp-project
GEE_SERVICE_ACCOUNT=your-service-account@...iam.gserviceaccount.com
GEE_KEY_PATH=.secret/your-key.json

# OpenWeather API
OPENWEATHER_KEY=your-api-key

# Google Gemini
GEMINI_API_KEY=your-api-key

# Africa's Talking
AT_APIKEY=your-apikey
AT_USERNAME=your-username
```

---

## 📣 Component Breakdown: What Each Part Does

### 1. **Google Earth Engine (GEE)** — Satellite Crop Analysis
**File:** `services/gee.py`

**Technology:** Google Earth Engine API + Python library
**Purpose:** Analyze vegetation health and rainfall patterns using FREE satellite data
**Datasets:** 
- MODIS/061/MOD13Q1 (NDVI — vegetation greenness) 250m resolution
- UCSB-CHG/CHIRPS/DAILY (rainfall) 5km resolution

**How It Works:**
1. Authenticates with GCP service account (no cost, public data)
2. For a given county, fetches last 30 days of MODIS NDVI data
3. Computes mean NDVI (0.0-1.0; higher = healthier vegetation)
4. Fetches last 30 days of CHIRPS rainfall
5. Compares to 365-day baseline → calculates anomaly %
6. Derives alert level:
   - **HIGH:** NDVI < 0.2 OR anomaly < -40% (severe drought)
   - **MEDIUM:** NDVI < 0.3 OR anomaly < -20% (moderate stress)
   - **LOW:** Otherwise (good conditions)

**Output:** `{"alert_level": "high", "ndvi": 0.54, "rainfall_anomaly": -100%, ...}`

**Caching:** Batch computation stored in `data/gee_alerts_latest.json` (daily refresh via `update_gee_summaries.py`)

**Why?** Satellite data is objective, covers entire regions, requires no ground infrastructure

---

### 2. **OpenWeather API** — Live Weather Context
**File:** `services/weather.py`

**Technology:** OpenWeather REST API (free tier)
**Purpose:** Get immediate weather conditions for validation and alerts
**Data:** Temperature, humidity, wind speed, cloud cover, condition (rain/clear/etc.)

**How It Works:**
1. When farmer enters a county, looks up OpenWeather for that location
2. Fetches current weather via free API
3. Returns all fields as dict: `{temp: 18, humidity: 95, wind_speed: 2, ...}`
4. If API unavailable or key missing, uses mock data (deterministic, based on county)

**Why?** Captures same-day conditions (rain, heat) that override longer-term trends

**Example:** GEE says "mild drought" but OpenWeather shows "heavy rain today" → system prioritizes short-term

---

### 3. **FAO Food Price Index** — Real Market Data
**File:** `services/fao_prices.py` + `services/market.py`

**Technology:** FAO (UN Food & Agriculture Org) commodity pricing
**Purpose:** Show farmers what their crops/livestock are worth NOW
**Covers:** 10 commodities (maize, beans, sorghum, millet, cassava, goat, sheep, chicken, dairy, fish)

**How It Works:**
1. FAO publishes monthly price data for key commodities
2. System caches prices locally (24-hour TTL) to avoid rate-limiting
3. When farmer requests market prices (Option 5), retrieves from cache
4. **SPECIAL:** If GEE detects drought in farmer's county, prices adjust:
   - High drought → +20% (scarcity premium, less supply)
   - Low risk → -5% (abundant harvest, oversupply)

**Example:**
```
Base maize price: 2600–3500 KES/bag (FAO)
Makueni county has HIGH drought (GEE)
Adjusted price: 3120–4200 KES/bag (+20%)
This tells farmers: "Yes, prices are higher now due to scarcity"
```

**Why?** Farmers need current market intelligence to decide what to sell/buy

---

### 4. **Google Gemini LLM** — AI Advice Generation
**File:** `services/advisory.py`

**Technology:** Google Generative AI (Gemini 2.5-flash model)
**Purpose:** Explain recommendations in natural, farmer-friendly language
**Input:** County, GEE risk, weather, farm size, budget, experience, alternatives

**How It Works:**
1. Collects all context: `"Farmer in Makueni, beginner, sandy soil, 2 acres, 50k budget. GEE shows high drought. Weather: 18°C, 95% humidity."`
2. Sends prompt to Gemini: `"Recommend from [sorghum, millet, cowpea, cassava]. Why is first choice best? Mention irrigation, disease, heat stress."`
3. Gemini responds with natural explanation (e.g., "Sorghum is drought-tolerant, needs less water. High humidity risks fungal disease—plant in wider rows.")
4. Truncates to 100 chars for USSD (SMS constraint)
5. If API fails or key missing, returns template advice (system still works)

**Why?** Farmers trust advice explained in their understanding, not just a number/code

---

### 5. **USSD Flow Manager** — User Interaction State Machine
**File:** `ussd_flow.py`

**Technology:** Stateless state machine using `*`-delimited text input
**Purpose:** Handle 9-option menu + multi-step flows (crop/livestock recommendation)
**Design:** No server-side sessions; state encoded in USSD text string

**How It Works:**

**Option 1-2 (Crop/Livestock Recommendation):**
```
Input: "1*Makueni*sandy*2*50000*1"
Parsed: [option=1, county=Makueni, soil=sandy, size=2, budget=50000, exp=1]
→ Calls recommender.get_recommendation() with all parameters
```

**Option 3-4 (Alerts) with Auto-Fill:**
```
If user county saved in profile:
  Input: "3"
  → Auto-fills county from user_store
  → Skips the "enter county" step
  
If no profile:
  Input: "3"
  → Asks for county
  Input: "3*Makueni"
  → Retrieves alert
```

**Option 7 (Seasonal Tips):**
```
Current month = May (rainy season in Kenya)
User farm_type = crop
→ Returns Crop Tips (Rainy Season): Prepare land, manage drainage, etc.
```

**Option 8 (Profile Edit):**
```
Input: "8" → Display profile + menu (edit which field?)
Input: "8*1" → Ask for new name
Input: "8*1*John Farmer" → Update + confirm
```

**Why USSD?** Works on ANY phone (even 20-year-old ones), only needs SMS/cellular

---

###  6. **Recommendation Engine** — Decision Logic
**File:** `recommender.py`

**Technology:** Rule-based ranking (transparent, no "black box" ML)
**Purpose:** Synthesize GEE, weather, farm data into top crop/livestock options
**Output:** Primary recommendation + ranked list of 3 alternatives

**How It Works:**

**Step 1: Load base options**
- Crops: sorghum, millet, cowpea, cassava, beans, maize
- Livestock: goat, sheep, chicken, dairy cattle

**Step 2: Apply GEE adjustments (satellite tells us)**
- High drought (NDVI <0.2)? → Prefer sorghum/millet (drought-tolerant)
- Good rainfall? → Keep maize/beans (water-loving)

**Step 3: Apply weather adjustments (immediate conditions)**
- High temp (≥30°C) + low humidity (drought)? → Shift to sorghum/millet
- High humidity (≥75%) for livestock? → Prefer dairy cattle (water-loving)

**Step 4: Apply farm constraints**
- Budget <10k? → Chicken (cheapest)
- Budget >50k? → Dairy/goat (higher investment)
- Experience = beginner? → Maize (safest, most known)
- Experience = expert? → Sorghum/millet (more complex)

**Step 5: Return top 4 options**
```
{
  "recommendation": "sorghum",
  "recommendation_options": ["millet", "cowpea", "cassava"],
  "weather": {...},
  "advice": "...",
  "gee_insights": {...}
}
```

**Why Rules Not ML?** 
- Transparent: farmer can ask "why sorghum?" and understand the logic
- No training needed: rules based on agronomic knowledge
- Fast: evaluates in <100ms
- Interpretable: can point to specific factors (GEE, weather, budget)

---

### 7. **Alert System** — Risk Notifications
**File:** `services/alerts.py`

**Technology:** GEE + OpenWeather context + rules
**Purpose:** Alert subscribed farmers to weather/disease risks with actionable advice
**Gating:** Subscription required (Option 9)

**Weather Alert:**
- GEE: alert level, NDVI, rainfall anomaly
- OpenWeather: live temp, humidity, wind, clouds
- Output: *"HIGH drought risk (NDVI=0.54, anomaly=-100%). Current conditions: 95% humidity, 2 m/s wind. Action: Monitor for fungal disease."*

**Disease Alert:**
- High humidity (≥80%) + temp 20-28°C? → **Fungal disease HIGH**
- High temp (≥30°C)? → **Pest/heat stress HIGH**
- Low rainfall (anomaly <-30%)? → **Crop stress HIGH**
- Output: *"Disease alert: HIGH risk. Fungal disease likely due to humidity 95%. Action: Spray fungicide, improve ventilation."*

**Why Both?** 
- GEE shows long-term drought trend
- OpenWeather shows immediate condition that triggers disease
- Together = actionable warning ("spray NOW because humidity is high")

---

### 8. **User Profiles** — Personalization Store
**File:** `user_store.py`

**Technology:** In-memory Python list + optional JSON persistence
**Purpose:** Remember farmer's preferences to enable auto-fill and personalization
**Stores:** name, county, farm_type, soil_type, subscription status

**How It Works:**
1. Demo users pre-loaded (Vin Demo, Amina Demo, etc.)
2. `get_user_by_phone("+254792246733")` → returns user dict
3. `update_user(phone, {county: "Makueni"})` → updates profile
4. When farmer uses USSD, their county auto-fills alerts, seasonal tips based on farm_type

**Why?** Reduces input steps for returning farmers

---

## 🔄 End-to-End Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│ Farmer Input (county, soil, size, budget, experience)       │
└─────────────────┬──────────────────────────────────────────┘
                  │
      ┌───────────┼───────────┬──────────────┐
      ▼           ▼           ▼              ▼
   ┌────────┐ ┌────────┐ ┌───────────┐ ┌──────────┐
   │  GEE   │ │Weather │ │   FAO     │ │Farm Data │
   │(NDVI,  │ │(Temp,  │ │ (Prices)  │ │(Soil,    │
   │Rainfall)│ │Humidity)│ │           │ │Budget)   │
   └───┬────┘ └───┬────┘ └─────┬─────┘ └────┬─────┘
       │          │            │            │
       └──────────┼────────────┼────────────┘
                  │            │
                  ▼            ▼
          ┌──────────────────────────────┐
          │ Recommendation Engine        │
          │ (Rule-based ranking)         │
          └───────┬───────┬──────────────┘
                  │       │
         ┌────────┘       └────────┐
         ▼                         ▼
    ┌─────────┐            ┌────────────┐
    │ Primary │            │ 3 + Others │
    │ Crop    │            │ (ranked)   │
    └────┬────┘            └─────┬──────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │ Gemini LLM           │
          │ (Generate advice)    │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │ USSD Response        │
          │ (plain text SMS)     │
          └──────────┬───────────┘
                     │
                     ▼
                Farmer's Phone
```

---

## 🧪 Testing Guide

### Test 1: Verify GEE Setup
```bash
python -c "from services.gee import init_gee; print(init_gee())"
# Expected: {'available': True, 'mode': 'service-account', 'message': 'initialized'}
```

### Test 2: Full Recommendation Flow
```bash
python -c "
from ussd_flow import handle_ussd
result = handle_ussd('1*Makueni*sandy*2*50000*1', '+254792246733')
print(result)
"
# Expected: Recommendation for sorghum + options + weather + advice
```

### Test 3: Market Prices with GEE Adjustment
```bash
python -c "
from services.market import get_market_prices
price = get_market_prices('maize', county='Makueni', gee_adjust=True)
print(f'Maize (Makueni): {price[\"min\"]}-{price[\"max\"]} {price[\"unit\"]}')
"
```

### Test 4: Weather Alert
```bash
python -c "
from services.alerts import build_weather_alert
alert = build_weather_alert('Makueni', subscribed=True)
print(alert)
"
```

### Test 5: Start Server + Send USSD Request
```bash
# Terminal 1
bash start.sh

# Terminal 2 (after server starts)
curl -X POST http://localhost:8000/ussd \
  -d "text=1*Makueni*sandy*2*50000*1&phoneNumber=%2B254792246733"
```

---

## 🚀 Deployment

### Local Development
```bash
bash start.sh      # FastAPI on 8000 + ngrok tunnel
bash stop.sh       # Stops services + clears ports
```

### Production (Render)
1. Push code to GitHub
2. Create Render web service from GitHub repo
3. Set environment variables on Render dashboard
4. Render auto-deploys on each push
5. Update Africa's Talking callback URL to Render domain

---

## 📊 Summary Table

| Component | Tech | Purpose | Why |
|-----------|------|---------|-----|
| **GEE** | Earth Engine | Satellite crop analysis | Free, global, objective data |
| **OpenWeather** | REST API | Live conditions | Immediate signals (rain, heat) |
| **FAO** | Price data | Market context | Real commodity prices |
| **Gemini** | LLM | Natural explanation | Farmers trust explained advice |
| **USSD** | State machine | User interface | Works on any phone |
| **Recommender** | Rules | Decision synthesis | Transparent, fast, interpretable |
| **Alerts** | GEE + Weather | Risk notifications | Actionable warnings |

---

## ✅ Features Summary

✅ **Satellite-Powered** — GEE provides NDVI & rainfall anomaly
✅ **Weather-Aware** — OpenWeather validates satellite signals
✅ **AI Reasoning** — Gemini explains "why" in 1-2 sentences
✅ **Real Prices** — FAO data with GEE scarcity adjustments
✅ **Multi-Option** — Primary + 3 ranked alternatives
✅ **Seasonal Tips** — Advisory changes by month + farm type
✅ **Profile Edit** — Farmers customize preferences
✅ **USSD-First** — Works on any phone, no internet required
✅ **Production-Ready** — Docker + Render + 24-hour caching

---

## 📖 Full Documentation

For detailed API reference, troubleshooting, and architecture diagrams, see [README_DETAILED.md](README_DETAILED.md).

---

## Ready to Test?

```bash
# 1. Verify setup
python -c "from services.gee import init_gee; print(init_gee())"

# 2. Start server
bash start.sh

# 3. Send test USSD (in another terminal)
curl -X POST http://localhost:8000/ussd \
  -d "text=1*Makueni*sandy*2*50000*1&phoneNumber=%2B254792246733"

# Expected: Recommendation with options, weather, and Gemini advice
```

---

Made with ❤️ for Kenyan farmers. Built for hackathons, ready for production.
