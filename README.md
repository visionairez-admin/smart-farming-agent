# 🌾 KrishiMitra — Smart Farming Agent

> An AI-powered Smart Farming Assistant for Indian farmers, built on **IBM watsonx.ai** with **Granite models**, Flask backend, and a responsive multilingual frontend.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Multi-Agent Architecture** | 5 specialist agents: Crop Advisory, Weather & Irrigation, Pest & Disease, Market Insights, Government Schemes |
| **IBM watsonx.ai + Granite** | Powered by `ibm/granite-3-3-8b-instruct` via the official `ibm-watsonx-ai` SDK |
| **RAG (Retrieval-Augmented Generation)** | Local agricultural knowledge base (crops, soil, pests, schemes) injected into every prompt |
| **Image Upload** | Upload crop photos for AI-powered pest and disease diagnosis |
| **Multilingual** | English, Hindi (हिंदी), Marathi (मराठी), Telugu, Tamil, Kannada, Punjabi |
| **Dark Mode** | Full dark/light theme toggle with persistent preference |
| **Responsive UI** | Mobile-first Bootstrap 5 with chat interface, dashboard, crop browser, scheme cards |
| **Farm Profile** | Personalised recommendations based on location, soil, water source, crops, and budget |
| **Government Schemes** | PM-KISAN, PMFBY, KCC, PMKSY, eNAM, Soil Health Card and more |

---

## 🏗️ Architecture

```
smart-farming-agent/
├── app.py                          # Flask app — orchestrator + API routes
├── rag_module.py                   # RAG retrieval from knowledge base
├── requirements.txt
├── .env.example                    # Environment variable template
│
├── agents/
│   ├── __init__.py
│   ├── base_agent.py               # Shared watsonx.ai client
│   ├── crop_agent.py               # Crop Advisory Agent
│   ├── weather_agent.py            # Weather & Irrigation Agent
│   ├── pest_agent.py               # Pest & Disease Detection Agent
│   ├── market_agent.py             # Market Insights Agent
│   └── schemes_agent.py            # Government Schemes Agent
│
├── knowledge_base/
│   └── agricultural_knowledge.json # Crop, soil, pest, scheme data
│
├── templates/
│   └── index.html                  # Main frontend (Jinja2 template)
│
├── static/
│   ├── css/style.css               # Custom styles + dark mode tokens
│   └── js/app.js                   # Frontend logic (no framework)
│
└── uploads/                        # Temporary image upload storage
```

---

## 🚀 Quick Start

### 1. Clone the project

```bash
cd smart-farming-agent
```

### 2. Create a Python virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
IBM_API_KEY=your_ibm_cloud_api_key_here
IBM_PROJECT_ID=your_watsonx_project_id_here
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
FLASK_SECRET_KEY=your_random_secret_key
```

### 5. Run the application

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## 🔑 Getting IBM watsonx.ai Credentials

1. **IBM Cloud API Key**
   - Log in to [IBM Cloud](https://cloud.ibm.com)
   - Go to **Manage → Access (IAM) → API Keys**
   - Click **Create an IBM Cloud API key**
   - Copy the key into your `.env` file

2. **watsonx.ai Project ID**
   - Open [IBM watsonx.ai](https://dataplatform.cloud.ibm.com/wx)
   - Create or open a project
   - Go to **Manage → General** and copy the **Project ID**

3. **IBM_WATSONX_URL** — Use the URL for your region:
   - US South: `https://us-south.ml.cloud.ibm.com`
   - EU Frankfurt: `https://eu-de.ml.cloud.ibm.com`
   - UK London: `https://eu-gb.ml.cloud.ibm.com`
   - Tokyo: `https://jp-tok.ml.cloud.ibm.com`

---

## 🤖 Customising Agent Behaviour

Each agent file contains an `AGENT_INSTRUCTIONS` constant that you can edit to customise behaviour **without touching any Python logic**:

| File | Constant | What to Customise |
|---|---|---|
| `app.py` | `ORCHESTRATOR_INSTRUCTIONS` | Agent persona, greeting, routing |
| `agents/crop_agent.py` | `CROP_AGENT_INSTRUCTIONS` | Crop specialisation, tone, safety rules |
| `agents/weather_agent.py` | `WEATHER_AGENT_INSTRUCTIONS` | Weather interpretation, irrigation rules |
| `agents/pest_agent.py` | `PEST_AGENT_INSTRUCTIONS` | IPM hierarchy, chemical safety, diagnosis format |
| `agents/market_agent.py` | `MARKET_AGENT_INSTRUCTIONS` | Market context, scheme mentions, selling advice |
| `agents/schemes_agent.py` | `SCHEMES_AGENT_INSTRUCTIONS` | Scheme list, application guidance |

### Example customisation (crop_agent.py):

```python
CROP_AGENT_INSTRUCTIONS = """
...
REGIONAL SPECIALISATION:
- You specialise in Vidarbha cotton farming (Maharashtra).
- Always mention Bt cotton regulations and Pink Bollworm resistance management.
- Refer to PDKV (Dr Panjabrao Deshmukh Krishi Vidyapeeth) research recommendations.
...
"""
```

---

## 🌐 API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Main frontend |
| `/api/chat` | POST | Send a text message to the AI |
| `/api/chat/image` | POST | Send an image for pest/disease analysis |
| `/api/profile` | GET/POST | Get or update farm profile |
| `/api/crops` | GET | List all crops from knowledge base |
| `/api/schemes` | GET | List all government schemes |
| `/api/calendar` | GET | Seasonal planting calendar |
| `/api/dashboard` | GET | Aggregated dashboard data |
| `/api/history` | GET | Conversation history |
| `/api/history/clear` | POST | Clear conversation history |
| `/api/health` | GET | API + watsonx.ai health status |

### Chat Request Example

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What fertilizer dose should I use for soybean?",
    "agent": "auto",
    "language": "en"
  }'
```

### Response

```json
{
  "response": "For soybean cultivation...",
  "agent_used": "crop",
  "session_id": "...",
  "timestamp": "2024-10-15T10:30:00"
}
```

---

## 🌾 Knowledge Base

The knowledge base (`knowledge_base/agricultural_knowledge.json`) contains:

- **8 major crops**: Rice, Wheat, Cotton, Soybean, Sugarcane, Maize, Groundnut, Turmeric
- **4 soil types**: Alluvial, Black Cotton, Red, Laterite
- **4 pests/diseases**: Fall Armyworm, Rice Blast, Cotton Bollworm, Powdery Mildew
- **7 government schemes**: PM-KISAN, PMFBY, KCC, PMKSY, eNAM, Soil Health Card, PM Maan Dhan
- **Seasonal calendar**: Kharif, Rabi, Zaid crops
- **Irrigation methods**: Drip, Sprinkler, Flood
- **Organic farming**: Bio-fertilizers, vermicompost, green manures

### Extending the Knowledge Base

Add new entries to the JSON arrays. The RAG module auto-indexes all entries on startup. No vector DB or retraining required — it uses fast keyword scoring.

---

## 🌍 Multilingual Support

Select a language from the navbar dropdown. The agent responds in:
- 🇬🇧 English (default)
- 🇮🇳 हिंदी (Hindi)
- 🌾 मराठी (Marathi)
- 🌾 తెలుగు (Telugu)
- 🌾 தமிழ் (Tamil)
- 🌾 ಕನ್ನಡ (Kannada)
- 🌾 ਪੰਜਾਬੀ (Punjabi)

---

## ☁️ Deployment

### Option A: Gunicorn (Production)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Option B: Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
```

```bash
docker build -t krishimitra .
docker run -p 5000:5000 --env-file .env krishimitra
```

### Option C: IBM Code Engine / Cloud Foundry

```bash
# Install IBM Cloud CLI + Code Engine plugin
ibmcloud ce app create \
  --name krishimitra \
  --image your-registry/krishimitra:latest \
  --env-from-secret krishimitra-secrets
```

---

## 🔒 Security Notes

- **Never commit your `.env` file** — it is listed in `.gitignore`
- API keys are loaded via `python-dotenv` at runtime only
- Uploaded images are stored temporarily in `/uploads/` — add cleanup cron for production
- Session data is stored server-side using Flask's signed cookie sessions
- Add HTTPS via reverse proxy (nginx/Caddy) before public deployment

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| AI Model | IBM watsonx.ai — `ibm/granite-3-3-8b-instruct` |
| Backend | Python 3.11+, Flask 3.0, Flask-CORS |
| RAG | Custom keyword-scored retriever (no vector DB needed) |
| Frontend | Bootstrap 5.3, Vanilla JS, Bootstrap Icons |
| Weather API | OpenWeatherMap (optional) |
| Image Processing | Pillow |
| Environment | python-dotenv |
| Production Server | Gunicorn |

---

## 📞 Farmer Helplines (Reference)

| Service | Number |
|---|---|
| Kisan Call Centre | 1800-180-1551 |
| PM-KISAN Helpline | 155261 |
| PMFBY Helpline | 1800-200-7710 |
| Soil Health Portal | soilhealth.dac.gov.in |
| eNAM | enam.gov.in |
| Poison Control | 1800-116-117 |

---

## 📄 License

MIT License — Free to use, modify, and distribute.

---

*Built with ❤️ for Indian farmers | Powered by IBM watsonx.ai*
