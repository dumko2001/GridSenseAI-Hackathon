# GridSense AI ⚡

**Advanced Renewable Generation Forecasting for Grid Stability.**

GridSense AI is a multi-model fusion system designed to provide plant-level and cluster-level solar and wind forecasts. It combines historical SCADA data with real-time weather covariates and physics-based constraints to deliver accurate, explainable dispatch guidance.

### 🌟 Key Features
- **Foundation Model Baseline:** Uses `chronos-bolt-small` for zero-shot forecasting across diverse asset types.
- **Weather Residual Layer:** Adjusts predictions based on real-time cloud cover and wind speed anomalies.
- **Physics-Enforced Logic:** Hard-clamped constraints (GHI caps, turbine power curves) to ensure operationally valid outputs.
- **Air-Gapped Explainability:** 100% offline, deterministic template explanations for grid operators.
- **Regulatory Ready:** Built-in benchmarking against CERC regulatory limits.

### 🚀 Quick Start (Local)
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the API:**
   ```bash
   python src/api/main.py
   ```
3. **Launch the Dashboard:**
   ```bash
   streamlit run dashboard/app.py
   ```

### 📦 Deployment
This repository is optimized for **Streamlit Cloud** or **Hugging Face Spaces**. Simply connect your GitHub account and point to `dashboard/app.py`.

---
*Built for the AI for Bharat Hackathon (Theme 10: AI for Renewable Generation Forecasting).*
