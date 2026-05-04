# GridSense AI — Run Instructions
**For Hackathon Jurors & Evaluators**

These instructions are designed to get the system running in **under 5 minutes** on any macOS, Linux, or Windows machine with Python 3.10+.

---

## Prerequisites

- Python 3.10 or higher
- 8 GB RAM minimum (16 GB recommended)
- Internet connection (for first-time model download from HuggingFace)
- No GPU required — runs on CPU

---

## Option A: Local Python Setup (Recommended for Demo)

### Step 1: Extract & Enter Directory
```bash
cd gridsense-prototype
```

### Step 2: Create Virtual Environment
```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```
*This downloads ~2GB of packages including PyTorch and Chronos-Bolt. Takes 3–5 minutes.*

### Step 4: Verify Data Exists
Pre-generated data is included in the submission:
```bash
ls data/synthetic_scada/synthetic_scada.csv
ls data/weather/weather_all.parquet
ls models/baseline/baseline_forecasts.parquet
```

If files are missing, regenerate them:
```bash
python src/data/scada_generator.py      # ~5 seconds
python src/data/weather_fetcher.py      # ~30 seconds
python src/pipeline/baseline_forecaster.py  # ~60 seconds
```

### Step 5: Run Tests
```bash
pytest tests/test_harness.py -v
```
Expected: **9 passed, 1 skipped**

### Step 6: Start the API Server
```bash
python src/api/main.py
```
You will see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Leave this terminal running. Open a browser to:
- **API docs:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/health

### Step 7: Start the Dashboard (New Terminal)
```bash
# Activate venv again
source venv/bin/activate  # (or venv\Scripts\activate on Windows)

streamlit run dashboard/app.py
```
You will see:
```
Local URL: http://localhost:8501
```

Open http://localhost:8501 in your browser.

### Step 8: Try the Dashboard
1. Select **"Pavagada Solar Park (100 MW)"** from the sidebar
2. Select horizon **"24"**
3. Click **"🚀 Generate Forecast"**
4. View the chart, insights, and physics alerts

---

## Option B: Docker (If Python Setup Fails)

Requires Docker Desktop installed.

```bash
cd gridsense-prototype
docker-compose up --build
```

Wait 5–10 minutes for the image to build. Then:
- API: http://localhost:8000
- Dashboard: http://localhost:8501

---

## Option C: Quick API Test (No Dashboard)

With the API server running:

```bash
# Health check
curl http://localhost:8000/health

# Solar forecast
curl -X POST http://localhost:8000/forecast \
  -H "Content-Type: application/json" \
  -d '{"plant_id":"SOL_PAVAGADA_100","prediction_hours":24}'

# Wind forecast
curl -X POST http://localhost:8000/forecast \
  -H "Content-Type: application/json" \
  -d '{"plant_id":"WIND_CHITRADURGA_80","prediction_hours":24}'
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'chronos'` | Ensure venv is activated: `source venv/bin/activate` |
| HuggingFace download hangs | Model downloads on first run. If slow, use a VPN or wait. ~500MB download. |
| Port 8000 already in use | Kill existing process: `lsof -ti:8000 \| xargs kill -9` then restart |
| Streamlit shows "Please wait" | The first forecast loads the Chronos model (~10s). Subsequent calls are instant. |
| Groq explanations fail | Check `.env` has `GROQ_API_KEY`. If missing, template explanations auto-activate. |
| Windows PowerShell won't activate venv | Use `venv\Scripts\Activate.ps1` or Command Prompt instead |

---

## Environment Variables (Optional)

Copy `.env.example` to `.env` and fill in:
```bash
GROQ_API_KEY=your_key_here    # For AI explanations (optional, fallback works without it)
API_URL=http://localhost:8000  # Dashboard talks to this API
```

**Privacy note:** The Groq API key is used ONLY for natural language explanations. No SCADA data or sensitive grid information is ever sent to Groq — only weather metadata (cloud %, wind speed, GHI).

---

## What You Should See

### API Response Example
```json
{
  "plant_id": "SOL_PAVAGADA_100",
  "timestamp": "2025-04-01 07:00:00",
  "forecast_MW": 21.4,
  "confidence_lower": 15.2,
  "confidence_upper": 28.1,
  "explanation": "At 07:00 IST, the solar generation forecast is 21.4 MW, slightly below baseline due to early morning clear-sky GHI constraints.",
  "was_clamped": true,
  "clamp_reason": "Capped by clear-sky GHI limit (152 W/m2)",
  "drivers": {
    "cloud_fraction": 0.0,
    "wind_speed_10m": null,
    "residual_MW": 0.0
  }
}
```

### Dashboard Screenshot Description
- **Left sidebar:** Plant selector, horizon picker, Generate button
- **Main chart:** Purple forecast line with lavender confidence band
- **Right panel:** Peak/min metrics, AI explanations, physics alerts
- **Bottom:** Hourly table with CSV download button

---

**Expected total setup time: 3–5 minutes.**
**If anything fails, the test harness will tell you exactly what's wrong: `pytest tests/test_harness.py -v`**
