# GridSense AI ⚡

**Advanced Renewable Generation Forecasting for Grid Stability.**

GridSense AI is a multi-model fusion system designed to provide plant-level and cluster-level solar and wind forecasts. It combines historical SCADA data with real-time weather covariates and physics-based constraints to deliver accurate, explainable dispatch guidance.

### 🌟 Key Features
- **Foundation Model Baseline:** Uses `chronos-bolt-small` for zero-shot forecasting across diverse asset types.
- **Weather Residual Layer:** Adjusts predictions based on real-time cloud cover and wind speed anomalies.
- **Physics-Enforced Logic:** Hard-clamped constraints (GHI caps, turbine power curves) to ensure operationally valid outputs.
- **Air-Gapped Explainability:** 100% offline, deterministic template explanations for grid operators.
- **Regulatory Ready:** Built-in benchmarking against CERC regulatory limits.

### 🚀 Quick Start (Local Setup)
To run the dashboard locally with the correct environment:

1. **Clone and Enter Repository:**
   ```bash
   git clone https://github.com/dumko2001/GridSenseAI-Hackathon.git
   cd GridSenseAI-Hackathon
   ```

2. **Create and Activate Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch Dashboard:**
   ```bash
   # We add src to the python path so modules are discovered correctly
   export PYTHONPATH=$PYTHONPATH:$(pwd)/src
   streamlit run dashboard/app.py
   ```

### 📦 Deployment
This repository is optimized for **Streamlit Cloud**. 
1. Connect your GitHub account.
2. Select this repository.
3. Set **Python Version to 3.12** (recommended).
4. Point the main file to `dashboard/app.py`.

---
*Built for the AI for Bharat Hackathon (Theme 10: AI for Renewable Generation Forecasting).*
