# Agritech
🌾 Agritech AI — Hack Night Demo

🔍 Overview

Agritech AI is a lightweight, AI-powered agricultural assistant accessible through USSD, making it usable by farmers with or without smartphones.
It provides crop and livestock recommendations based on region, soil type, and weather using mock AI data.
This demo is designed for hackathons, runs fully offline with mock data, and can easily integrate live APIs later.


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
Deployment	Ngrok (tunnel for Africa’s Talking callback)
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
