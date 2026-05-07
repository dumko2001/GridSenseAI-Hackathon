# GridSense AI Prototype

> **AI-based renewable generation forecasting system for Karnataka SLDCs.**  
> Built for Theme 10: AI for Renewable Generation Forecasting by KREDL / KSPDCL.

## What This Is

GridSense AI predicts solar and wind power generation for the next 6–48 hours using a 4-pass pipeline:

1. **Baseline Forecast** — Amazon Chronos-Bolt foundation model learns historical patterns
2. **Residual Adjustment** — Real-time weather data corrects for sudden cloud cover / wind changes
3. **Physics Validation** — Turbine power curves and solar irradiance caps ensure physically possible output
4. **Offline Explainability & Confidence** — Deterministic multilingual templates and aligned confidence bands

Every forecast includes **confidence bands** and a **natural language explanation** for grid operators.

## Quick Start

```bash
cd gridsense-prototype
./scripts/bootstrap_external.sh

# Verify everything works
./scripts/run_tests_external.sh

# Start API
./scripts/run_api_external.sh
# → http://localhost:8000/docs

# Start Dashboard (new terminal)
./scripts/run_dashboard_external.sh
# → http://localhost:8501
```

**Full setup guide:** [`RUN_INSTRUCTIONS.md`](RUN_INSTRUCTIONS.md)  
**Submission checklist:** [`SUBMISSION.md`](SUBMISSION.md)

## Architecture

```
Historical SCADA CSV
        ↓
┌─────────────────┐
│  Chronos-Bolt   │  ← Zero-shot time series foundation model
│  Baseline       │
└────────┬────────┘
         ↓ forecast + quantiles
┌─────────────────┐
│  Weather Resid. │  ← Open-Meteo cloud cover → MW adjustment
│  Adjustment     │
└────────┬────────┘
         ↓ adjusted forecast
┌─────────────────┐
│  Physics Clamp  │  ← Clear-sky GHI, turbine curves, capacity limits
│  Validation     │
└────────┬────────┘
         ↓ final forecast
┌─────────────────┐
│  Explainability │  ← Offline deterministic template engine
│  + Confidence   │
└─────────────────┘
         ↓ JSON / CSV / Dashboard
```

## Key Features

| Feature | Status |
|---------|--------|
| Solar & wind forecasts | ✅ 3 solar plants + 2 wind clusters |
| Hourly granularity | ✅ 1-hour resolution |
| Day-ahead (24h) | ✅ Default horizon |
| Intra-day updates | ✅ Any horizon 1–48h selectable |
| Uncertainty quantification | ✅ Confidence bands (0.1 / 0.9 quantiles) |
| Operational explainability | ✅ Deterministic local templates |
| Physics constraints | ✅ GHI caps, turbine curves, rated limits |
| No SCADA modification | ✅ Reads CSV only |
| Works with synthetic data | ✅ Fully reproducible synthetic generator |
| No hosted LLM on sensitive data | ✅ No external AI APIs used |
| API-first integration | ✅ FastAPI with auto-docs |
| Interactive dashboard | ✅ Streamlit with Plotly charts |
| Bulk batch forecasting | ✅ CSV upload returns forecast CSV |
| Cluster aggregation | ✅ Aggregate any plant list into a regional forecast |
| Kannada explanations | ✅ Offline template support for `language=kn` |
| Docker deployment | ✅ Dockerfile + docker-compose.yml |

## Test Results

```
pytest tests/test_harness.py -v

16 passed
```

- Data pipeline integrity ✅
- Baseline beats persistence by 20.4% ✅
- Residual layer catches cloud events ✅
- Physics constraints prevent over-generation ✅
- Full API flows verified: plant, cluster, bulk, override, compliance ✅
- Explanations are non-empty, deterministic, and multilingual-ready ✅
- End-to-end orchestrator runs successfully ✅
- Current compliance report is CERC-compliant across all five benchmark assets ✅

## Project Structure

```
gridsense-prototype/
├── src/
│   ├── data/
│   │   ├── scada_generator.py      # Synthetic Karnataka plant data
│   │   └── weather_fetcher.py      # Open-Meteo integration
│   ├── pipeline/
│   │   ├── baseline_forecaster.py  # Chronos-Bolt inference
│   │   ├── residual_adjuster.py    # Weather-based residual rules
│   │   ├── physics_constraints.py  # Power curve & GHI clamps
│   │   ├── explainability.py       # Offline deterministic explanations
│   │   └── orchestrator.py         # End-to-end pipeline glue
│   └── api/
│       └── main.py                 # FastAPI backend
├── dashboard/
│   └── app.py                      # Streamlit frontend
├── tests/
│   └── test_harness.py             # Automated QA
├── data/                           # Generated (synthetic SCADA, weather)
├── models/                         # Generated (forecasts, metrics)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md
├── RUN_INSTRUCTIONS.md
├── SUBMISSION.md
└── EXPLANATIONS_AND_ROADMAP.md
```

## Tech Stack

| Layer | Tool | License |
|-------|------|---------|
| Baseline Model | Amazon Chronos-Bolt-Small | Apache 2.0 |
| Weather Data | Open-Meteo API | CC-BY 4.0 |
| Satellite (future) | ISRO MOSDAC + Satpy | Free / GPL-3.0 |
| Physics | Custom rule-based | — |
| Explainability | Local deterministic templates | Internal logic |
| API | FastAPI + Uvicorn | MIT |
| Dashboard | Streamlit + Plotly | Apache 2.0 |
| Testing | pytest | MIT |
| Deployment | Docker + Docker Compose | Apache 2.0 |

## API Example

```bash
curl -X POST http://localhost:8000/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "plant_id": "SOL_PAVAGADA_100",
    "context_hours": 168,
    "prediction_hours": 24
  }'
```

Response:
```json
[
  {
    "plant_id": "SOL_PAVAGADA_100",
    "timestamp": "2025-04-01 07:00:00",
    "forecast_MW": 21.4,
    "confidence_lower": 15.2,
    "confidence_upper": 28.1,
    "explanation": "At 07:00 IST, the solar generation forecast is 21.4 MW...",
    "was_clamped": true,
    "clamp_reason": "Capped by clear-sky GHI limit (152 W/m2)",
    "drivers": {
      "cloud_fraction": 0.0,
      "wind_speed_10m": null,
      "residual_MW": 0.0
    }
  }
]
```

## Demo Video Script (3 Minutes)

1. **0:00–0:30** — Problem: Karnataka's 30 GW renewable capacity creates grid volatility. DSM penalties for forecast errors.
2. **0:30–1:15** — Dashboard walkthrough: select Pavagada Solar, generate 24h forecast, show chart + confidence band
3. **1:15–1:45** — Show physics alerts: "Capped by clear-sky GHI limit" and operator explanation
4. **1:45–2:15** — API demo: curl request → JSON response with uncertainty + drivers
5. **2:15–2:45** — Architecture slide: baseline → residual → physics → explainability
6. **2:45–3:00** — Closing: on-premise ready, sovereign data, zero SCADA changes

## License & Attribution

Prototype built for hackathon evaluation. Production components retain their original open-source licenses:
- Chronos-Bolt: Apache 2.0 (Amazon Science)
- Open-Meteo: CC-BY 4.0 / AGPL-3.0
- FastAPI: MIT
- Streamlit: Apache 2.0

GridSense AI wrapper IP: the multi-pass fusion architecture, physics constraint layer, and explainability pipeline.

---

**Ready for a judge demo from the external-drive workflow. See `RUN_INSTRUCTIONS.md` for the exact run path.**
