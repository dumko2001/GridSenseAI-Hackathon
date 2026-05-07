# GridSense AI — Demo Presentation Outline
## Theme 10: AI for Renewable Generation Forecasting by KREDL / KSPDCL

**Target duration:** 3 minutes (180 seconds)  
**Format:** Screen recording with voiceover OR live demo  
**Audience:** Hackathon jury (mix of engineers, IAS officers, investors)

---

## Slide 1: Title (0:00–0:10)

**Visual:** Logo + dashboard screenshot  
**Script:**
> "GridSense AI. An AI-powered forecasting layer for Karnataka's renewable energy plants. Zero SCADA modifications. Runs on your laptop. Ready for the State Data Centre."

**On screen:**
- ⚡ GridSense AI
- "Renewable Generation Forecasting for Karnataka SLDCs"
- Subtitle: "Plant-level · Cluster-level · Day-ahead · Intra-day"

---

## Slide 2: The Problem (0:10–0:30)

**Visual:** Simple 3-panel diagram  
**Script:**
> "Karnataka has 5,000+ MW of solar and wind. But SLDC operators still schedule generation using yesterday's numbers. The result? Three problems. One: forecasting error costs ₹3–5 per unit in DSM penalties. Two: operators don't know WHY a forecast changed. Three: every new plant needs months of data collection before any model works."

**On screen:**
1. **Numerical Gap** — Persistence baseline = expensive errors
2. **Explainability Gap** — Black box models = operator distrust
3. **Onboarding Gap** — New plants need 6–12 months of history

---

## Slide 3: The Solution (0:30–0:50)

**Visual:** Architecture diagram (4-pass pipeline)  
**Script:**
> "GridSense AI uses a 4-pass fusion architecture. Pass 1: A foundation time-series model reads 7 days of SCADA history and predicts the next 24 hours. Pass 2: Real-time weather data from Open-Meteo adjusts for sudden cloud cover or wind shifts. Pass 3: Physics constraints enforce turbine power curves and solar irradiance limits. Pass 4: A deterministic local explanation engine explains every forecast in operator-ready language."

**On screen:**
```
SCADA History → [Baseline] → [Residual] → [Physics] → [Explain] → Forecast
     ↑                              ↑
     └────── 7 days (168h) ─────────┘      Weather (Open-Meteo)
```

---

## Slide 4: Live Demo — Plant Forecast (0:50–1:30)

**Visual:** Screen recording of Streamlit dashboard  
**Script:**
> "Let me show you. I open the dashboard. I select Pavagada Solar Park — 100 megawatts. I choose a 24-hour horizon. Click Generate. Three seconds later, I see a forecast. Peak generation tomorrow at 1 PM: 66 megawatts. The lavender band around the line is our uncertainty — the plant could produce as little as 58 or as much as 75. Every hour has a natural language explanation. At 1 PM: 'Solar generation forecast is 66.5 MW, adjusted downward 18 megawatts due to 37% cloud cover.' The operator knows exactly why."

**Actions to show:**
1. Sidebar: Select "☀️ Pavagada Solar Park (100 MW)"
2. Horizon: 24h
3. Click "Generate Forecast"
4. Point to: Peak metric, uncertainty band, insight card
5. Scroll down to table showing hourly detail

---

## Slide 5: Live Demo — Cluster Aggregation (1:30–1:50)

**Visual:** API call in terminal OR dashboard  
**Script:**
> "Now let's look at the cluster level. Karnataka SLDC doesn't schedule one plant at a time — they manage regions. I call the cluster endpoint with three plants: Pavagada, Koppal, and Chitradurga Wind. The API returns an aggregated forecast with a per-plant breakdown. Total cluster peak: 94 megawatts. Pavagada contributes 66, Koppal 22, wind 6. Flexible, on-demand aggregation for any regional grouping."

**Actions to show:**
```bash
curl -X POST http://localhost:8000/forecast/cluster \
  -H "Content-Type: application/json" \
  -d '{"plant_ids":["SOL_PAVAGADA_100","SOL_KOPPAL_50","WIND_CHITRADURGA_80"]}'
```
Show JSON response with `aggregated_forecast_MW` and `plant_breakdown`.

---

## Slide 6: Deployability & Sovereignty (1:50–2:15)

**Visual:** Docker + laptop + government building icons  
**Script:**
> "This is built for government deployment. It runs entirely on CPU — no GPU needed. One Docker command spins up the full stack. It never modifies existing SCADA systems — we read exported CSV files and return JSON forecasts. For data sovereignty, we use NASA POWER satellite irradiance and Open-Meteo weather. No foreign APIs with data residency concerns. And the explainability engine works fully offline — no sensitive SCADA data ever leaves the building."

**On screen:**
- ✅ CPU-only (8GB RAM)
- ✅ Docker Compose (1 command)
- ✅ Zero SCADA modifications
- ✅ Sovereign data (NASA + Open-Meteo)
- ✅ Air-gappable (offline explainability)

---

## Slide 7: Results & Baseline (2:15–2:35)

**Visual:** Metrics card  
**Script:**
> "How accurate is it? On our test suite, GridSense AI achieves an RMSE of 33.9 megawatts against a naive persistence baseline of 42.6. That's a 20% improvement — and this is a zero-shot model that has never seen these specific plants before. With real SCADA data and a production-grade model like Chronos-2, we expect 25–30% improvement."

**On screen:**
| Metric | Value |
|--------|-------|
| RMSE (GridSense) | 33.9 MW |
| RMSE (Persistence) | 42.6 MW |
| Improvement | **20.4%** |
| Model | Zero-shot (no training) |

---

## Slide 8: The Ask & Vision (2:35–2:55)

**Visual:** Karnataka map with 5 plant pins + future expansion arrows  
**Script:**
> "GridSense AI is ready for pilot deployment today. We are asking KREDL and KSPDCL for a 3-month pilot at 5 plants, expanding to 50 plants by year end. The software is open-source. The compute runs on existing State Data Centre infrastructure. And every rupee saved in DSM penalties is a rupee that can fund more renewable capacity for Karnataka. Thank you."

**On screen:**
- 🎯 3-month pilot @ 5 plants
- 📈 Scale to 50 plants by Q4
- 💰 Open-source stack = zero licensing cost
- 🏛️ Runs on State Data Centre (sovereign infra)

---

## Slide 9: Q&A / Contact (2:55–3:00)

**Visual:** GitHub repo QR code + email  
**Script:**
> "Questions? The full code, documentation, and one-command setup are at this repository. Thank you for your time."

**On screen:**
- GitHub: `github.com/[your-handle]/gridsense-prototype`
- Email: [your-email]
- One-command run: `docker-compose up --build`

---

## Demo Recording Checklist

**Before you hit record:**
- [ ] Terminal window sized to 100×30 (clean, no personal paths)
- [ ] Browser zoom at 110% for dashboard readability
- [ ] API server running in background terminal
- [ ] Dashboard already open at `localhost:8501`
- [ ] No notifications / pop-ups enabled
- [ ] Dark mode OFF (jury prefers light UI)
- [ ] Microphone tested, background noise minimized

**Recording flow:**
1. Start recording
2. Open terminal → run `pytest tests/test_harness.py -v` (shows tests passing)
3. Open browser → show dashboard welcome state
4. Select plant → generate forecast → narrate insights
5. Open terminal → run cluster curl command → show JSON
6. Switch back to dashboard → download CSV → show file
7. End with architecture diagram + contact slide

**Post-production:**
- Trim pauses (target: exactly 3:00)
- Add captions for key numbers (20.4% improvement, 33.9 MW RMSE)
- Background music: optional, keep subtle
- Export: 1080p MP4, under 100MB for upload

---

## Optional: Live Demo Backup Plan

If the jury asks for a live demo and something breaks:

| Failure | Backup |
|---------|--------|
| API won't start | Show pre-recorded screen capture |
| Model download slow | Say "First load takes 30s, then it's instant" |
| Explanation text questioned | Show the deterministic explanation logic and emphasize offline compliance |
| No internet | Show offline mode: template explanations + cached forecasts |

**Always have the pre-recorded video as primary submission. Live demo is bonus.**
