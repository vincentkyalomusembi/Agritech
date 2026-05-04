# Agritech
🌾 Agritech AI — Hack Night Demo

🔍 Overview

Agritech AI is a lightweight, AI-powered agricultural assistant accessible through USSD, making it usable by farmers with or without smartphones.
It provides crop and livestock recommendations based on region, soil type, and weather using mock AI data.
This demo is designed for hackathons, runs fully offline with mock data, and can easily integrate live APIs later.


---

📈 Detailed Project Workflow

This section explains the full flow of the project from the moment a farmer dials the USSD code to the moment the system returns a recommendation or alert.

### 1) Farmer starts the interaction
- The farmer dials the Africa’s Talking USSD shortcode.
- The request is sent to the FastAPI backend through the public ngrok or Render URL.

**Image placeholder**

![USSD entry flow](docs/images/01-ussd-entry.png)

### 2) FastAPI receives the USSD request
- The `/ussd` endpoint receives the `text` and `phoneNumber` values.
- `ussd_flow.py` reads the current menu state and decides the next response.
- If the request is empty, the main menu is shown.

**Image placeholder**

![FastAPI request handling](docs/images/02-fastapi-ussd-handler.png)

### 3) User selects a service
- Option 1: Crop Recommendation
- Option 2: Livestock Recommendation
- Option 3: Weather Alerts
- Option 4: Disease Alerts
- Option 5: Market Prices
- Option 6: Request Expert Visit
- Option 7: Advisory Tips
- Option 8: My Profile
- Option 9: Subscribe

**Image placeholder**

![USSD menu](docs/images/03-ussd-menu.png)

### 4) The recommendation engine builds context
- `recommender.py` loads the county and farm type.
- It collects weather from OpenWeather.
- It loads cached GEE results first for speed.
- If the cache is missing, it falls back to live Earth Engine.
- It combines soil, weather, GEE risk, farm size, budget, and experience.

**Image placeholder**

![Recommendation pipeline](docs/images/04-recommendation-pipeline.png)

### 5) GEE performs heavy analysis
- `services/gee.py` computes:
  - NDVI from MODIS
  - rainfall totals from CHIRPS
  - rainfall anomaly percentage
  - alert level: low, medium, or high
- The result is saved in `data/gee_alerts_latest.json` by the cache updater.

**Image placeholder**

![GEE data processing](docs/images/05-gee-processing.png)

### 6) OpenWeather provides local weather context
- `services/weather.py` returns:
  - temperature
  - feels-like temperature
  - humidity
  - wind speed
  - cloud cover
  - condition text
- This is used as supporting context for the recommendation and the alerts.

**Image placeholder**

![Weather API context](docs/images/06-openweather.png)

### 7) Gemini writes the human-readable advice
- `services/advisory.py` sends a structured prompt to Gemini.
- Gemini receives GEE, weather, and farm inputs.
- The response is turned into a short farmer-friendly explanation.

**Image placeholder**

![Gemini advice generation](docs/images/07-gemini-advice.png)

### 8) The USSD response is returned
- `ussd_flow.py` formats the final response.
- For recommendations, it now shows:
  - primary option
  - multiple alternative options
  - weather summary
  - a short advice preview
- For alerts, it shows the GEE risk and live weather conditions.

**Image placeholder**

![Final USSD response](docs/images/08-final-ussd-response.png)

### 9) Subscription and alerts flow
- Users subscribe through option 9.
- Subscribed users can access weather and disease alerts.
- Weather alerts combine OpenWeather conditions and GEE risk.
- Disease alerts combine rainfall anomaly, humidity, and heat stress.

**Image placeholder**

![Subscription and alerts](docs/images/09-subscription-alerts.png)

### 10) Deployment workflow
- Local development runs with `uvicorn`.
- `ngrok` exposes the app publicly for Africa’s Talking testing.
- Render can host the backend in production.
- GEE cache updates can be scheduled separately.

**Image placeholder**

![Deployment workflow](docs/images/10-deployment.png)

### Suggested workflow images to add

Place screenshots or diagrams in this folder:

```text
docs/images/
```

Recommended filenames:

- `01-ussd-entry.png`
- `02-fastapi-ussd-handler.png`
- `03-ussd-menu.png`
- `04-recommendation-pipeline.png`
- `05-gee-processing.png`
- `06-openweather.png`
- `07-gemini-advice.png`
- `08-final-ussd-response.png`
- `09-subscription-alerts.png`
- `10-deployment.png`



---

🧠 Key Features

🌍 Works on USSD — no internet or smartphone needed.

🤖 AI-like logic using mock data (expandable to real ML model).

🌦️ Optional Weather API integration.

💬 Real-time interaction using Africa’s Talking USSD API.

🪶 Lightweight and fast — ideal for a hack night prototype.



---

🧰 Tech Stack

Layer	Tool

Backend	FastAPI (Python)
Deployment	Ngrok (local tunnel) / Render (production)
SMS/USSD	Africa’s Talking Sandbox
Environment	Python 3.9+
Data	mock_data.json (editable)
AI (optional)	Decision Tree logic (local)



---

🗂️ Folder Structure

Agritech_ai_demo/
│
├── app.py                  # Main FastAPI backend
├── mock_data.json          # Mock AI + soil/weather data
├── .env                    # Secrets and API keys
├── requirements.txt        # Project dependencies
├── README.md               # Documentation
└── .gitignore              # Ignore files like __pycache__ or .env


---

⚙️ Setup Instructions

1️⃣ Clone the Repository

git clone https://github.com/<your-username>/Agritech_ai_demo.git
cd Agritech_ai_demo

2️⃣ Create and Activate Virtual Environment

python3 -m venv venv
source venv/bin/activate   # On Windows use venv\Scripts\activate

3️⃣ Install Dependencies

pip install -r requirements.txt

4️⃣ Add Environment Variables

Create a .env file:

AT_API_KEY=your_africastalking_api_key
AT_USERNAME=sandbox
WEATHER_API_KEY=your_weather_api_key   # optional

5️⃣ Run the Server

uvicorn app:app --reload --port 8000

6️⃣ Expose with Ngrok

ngrok http 8000

Copy the Forwarding URL (e.g., https://xxxx.ngrok-free.app).


---

🚀 Deploying on Render

1. Push this repository to GitHub.
2. Create a new **Web Service** on Render.
3. Connect the repo and choose the branch you want to deploy.
4. Render will use the included `Dockerfile` automatically.
5. Add your environment variables in Render:

```bash
OPENWEATHER_API_KEY=...
GEMINI_API_KEY=...
AT_API_KEY=...
AT_USERNAME=sandbox
GEE_PROJECT_ID=...
GEE_SERVICE_ACCOUNT=...
GEE_KEY_PATH=...
```

6. Deploy and use the Render URL for your Africa’s Talking callback:

```text
https://your-app.onrender.com/ussd
```

7. Health check endpoint:

```text
https://your-app.onrender.com/health
```


---

☁️ Africa’s Talking Setup

1. Go to Africa’s Talking Sandbox.


2. Navigate to USSD → Create Channel.


3. Enter:

Shortcode: Use the default or custom one.

Callback URL: https://xxxx.ngrok-free.app/ussd



4. Save changes.




---

📱 Testing

Dial your sandbox short code (e.g., *384*1234#) and follow the menu:

Welcome to Agritech AI
1. Get Recommendation
2. About


---

🧩 Mock Data Example (mock_data.json)

{
  "regions": {
    "Meru": {
      "soil": "loamy",
      "weather": "mild",
      "recommendation": "Beans, maize, or poultry."
    },
    "Nakuru": {
      "soil": "clay",
      "weather": "cool",
      "recommendation": "Potatoes, dairy cattle."
    },
    "Machakos": {
      "soil": "sandy",
      "weather": "hot",
      "recommendation": "Goats and drought-resistant crops like millet."
    }
  }
}

You can easily extend this file with more regions or dynamic predictions.


---

🧠 AI Logic (Optional Enhancement)

You can integrate a simple Decision Tree model or logic like:

def ai_recommendation(soil, weather):
    if soil == "loamy" and weather == "mild":
        return "Beans or poultry"
    elif soil == "clay":
        return "Potatoes or dairy"
    else:
        return "Goats or millet"


---

👥 Team Collaboration

Role	Task

Backend Dev	Build FastAPI + integrate AT + Ngrok
Data Engineer	Prepare mock_data.json and AI logic
Pitch Lead	Build presentation in Canva & explain impact


> Use GitHub for collaboration:



git add .
git commit -m "add ussd logic"
git push origin demo


---

🧪 Hack Night Timeline (Suggested)

Time	Task	Duration

0–1 hr	Setup repo + environment	1 hr
1–3 hr	Backend + mock data integration	2 hrs
3–5 hr	Africa’s Talking + Ngrok testing	2 hrs
5–6 hr	Add simple AI logic	1 hr
6–8 hr	Final testing + pitch preparation	2 hrs



---

💰 Monetization (For Pitch Deck)

Farmers pay Ksh 5–10 per USSD session for AI advice.

Partner with county governments and agri suppliers.

Use aggregated insights for B2B analytics later.

Expand to SMS, mobile app, and WhatsApp bot for premium services.



---

🚀 Future Enhancements

Real-time weather integration.

Predictive analytics using ML models.

Offline caching for field agents.

Livestock disease prediction.

Farmer-to-farmer marketplace module.


---

🛰️ Google Earth Engine (GEE) Quick Start

1. Enable Earth Engine API in your Google Cloud project.
2. Configure authentication (recommended: Service Account).
3. Add these environment variables:

```
GEE_PROJECT_ID=your_gcp_project_id
GEE_SERVICE_ACCOUNT=your-service-account@your-project.iam.gserviceaccount.com
GEE_KEY_PATH=/absolute/path/to/service-account-key.json
```

4. Generate county summaries (batch mode):

```bash
source env/bin/activate
python scripts/update_gee_summaries.py
```

5. Read results from API:

- `GET /gee/alerts/{county}` for live on-demand insights.
- `GET /gee/alerts-cache` for latest batch-cached summaries.

6. USSD menu changes:

- `1` and `2` now enrich recommendations with GEE and Gemini context.
- `3` and `4` are subscriber-only and include GEE-aware alert summaries.
- `9` subscribes the current USSD phone number for alerts.



---

🏆 Summary

Agritech AI empowers farmers with real-time, AI-backed advice — accessible even on a basic phone.
This demo shows how inclusive technology can revolutionize agriculture in Kenya and beyond.
