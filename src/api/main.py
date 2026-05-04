"""
GridSense AI - FastAPI Backend
Serves forecasts via REST API for SLDC integration.
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

import pickle
import pandas as pd
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import io

# Import pipeline modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data.scada_generator import PLANTS
from pipeline.baseline_forecaster import load_pipeline, forecast_baseline
from pipeline.residual_adjuster import apply_residual_layer
from pipeline.physics_constraints import apply_physics_constraints
from pipeline.explainability import generate_explanations

app = FastAPI(title="GridSense AI Forecast API", version="0.1.0")

# Lazy-load model on first request
_pipeline = None

def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = load_pipeline()
    return _pipeline


class ForecastRequest(BaseModel):
    plant_id: str
    context_hours: int = 168  # 7 days history
    prediction_hours: int = 24


class ForecastResponse(BaseModel):
    plant_id: str
    timestamp: str
    forecast_MW: float
    confidence_lower: float
    confidence_upper: float
    explanation: str
    was_clamped: bool
    clamp_reason: Optional[str] = None
    drivers: dict


class ClusterForecastRequest(BaseModel):
    plant_ids: List[str]
    context_hours: int = 168
    prediction_hours: int = 24


class ClusterForecastResponse(BaseModel):
    cluster_name: str
    timestamp: str
    aggregated_forecast_MW: float
    confidence_lower: float
    confidence_upper: float
    plant_breakdown: List[dict]
    key_drivers: str


@app.get("/health")
def health():
    return {"status": "ok", "model": "amazon/chronos-bolt-small", "version": "0.1.0"}


@app.post("/forecast", response_model=List[ForecastResponse])
def forecast(req: ForecastRequest):
    pipeline = get_pipeline()

    # Load full dataset (in production this would query a DB)
    scada = pd.read_csv("data/synthetic_scada/synthetic_scada.csv", parse_dates=["timestamp"])
    weather = pd.read_parquet("data/weather/weather_all.parquet")
    scada["timestamp"] = pd.to_datetime(scada["timestamp"]).dt.tz_localize(None)
    weather["timestamp"] = pd.to_datetime(weather["timestamp"]).dt.tz_localize(None)

    ctx = scada[scada["plant_id"] == req.plant_id].copy()
    if ctx.empty:
        return []

    # Take last context_hours
    ctx = ctx.sort_values("timestamp").tail(req.context_hours)

    # Run baseline
    pred_df = forecast_baseline(pipeline, ctx, prediction_length=req.prediction_hours)
    pred_df["plant_id"] = req.plant_id

    # Build future weather slice for residual (next prediction_hours after context end)
    last_ts = ctx["timestamp"].max()
    future_weather = weather[
        (weather["plant_id"] == req.plant_id) &
        (weather["timestamp"] > last_ts) &
        (weather["timestamp"] <= last_ts + pd.Timedelta(hours=req.prediction_hours))
    ].copy()

    # Residual
    pred_df = apply_residual_layer(pred_df, future_weather, PLANTS)
    # Physics
    pred_df = apply_physics_constraints(pred_df, future_weather, PLANTS)
    # Explainability (offline template by default; Groq optional via env)
    use_groq = os.getenv("ENABLE_GROQ", "false").lower() == "true"
    pred_df = generate_explanations(pred_df, use_api=use_groq)

    results = []
    for _, row in pred_df.iterrows():
        results.append(ForecastResponse(
            plant_id=row["plant_id"],
            timestamp=str(row["timestamp"]),
            forecast_MW=round(float(row.get("final_forecast_MW", row.get("predictions", 0))), 3),
            confidence_lower=round(float(row.get("0.1", row.get("predictions", 0) * 0.9)), 3),
            confidence_upper=round(float(row.get("0.9", row.get("predictions", 0) * 1.1)), 3),
            explanation=row.get("explanation", ""),
            was_clamped=bool(row.get("was_clamped", False)),
            clamp_reason=row.get("clamp_reason", None),
            drivers={
                "cloud_fraction": round(float(row.get("cloud_fraction", 0)), 3),
                "wind_speed_10m": round(float(row.get("wind_speed_10m", 0)), 2),
                "residual_MW": round(float(row.get("residual_MW", 0)), 3),
            }
        ))
    return results


@app.post("/forecast/bulk")
def forecast_bulk(file: UploadFile = File(...)):
    """Upload CSV with columns: plant_id, timestamp. Returns forecast CSV."""
    contents = file.file.read()
    df = pd.read_csv(io.StringIO(contents.decode("utf-8")), parse_dates=["timestamp"])
    # For prototype, return simple message
    return {"message": "Bulk forecast endpoint ready", "received_rows": len(df)}


@app.post("/forecast/cluster", response_model=List[ClusterForecastResponse])
def forecast_cluster(req: ClusterForecastRequest):
    """
    Aggregate forecasts across multiple plants (cluster/region level).
    Sums individual plant forecasts and combines confidence bands.
    """
    pipeline = get_pipeline()
    scada = pd.read_csv("data/synthetic_scada/synthetic_scada.csv", parse_dates=["timestamp"])
    weather = pd.read_parquet("data/weather/weather_all.parquet")
    scada["timestamp"] = pd.to_datetime(scada["timestamp"]).dt.tz_localize(None)
    weather["timestamp"] = pd.to_datetime(weather["timestamp"]).dt.tz_localize(None)

    all_plant_forecasts = []
    for pid in req.plant_ids:
        ctx = scada[scada["plant_id"] == pid].copy().sort_values("timestamp").tail(req.context_hours)
        if len(ctx) < req.prediction_hours * 2:
            continue
        pred_df = forecast_baseline(pipeline, ctx, prediction_length=req.prediction_hours)
        pred_df["plant_id"] = pid
        # Rename quantile columns for consistency
        if "0.1" in pred_df.columns:
            pred_df["confidence_lower"] = pred_df["0.1"]
        if "0.9" in pred_df.columns:
            pred_df["confidence_upper"] = pred_df["0.9"]
        last_ts = ctx["timestamp"].max()
        future_weather = weather[
            (weather["plant_id"] == pid) &
            (weather["timestamp"] > last_ts) &
            (weather["timestamp"] <= last_ts + pd.Timedelta(hours=req.prediction_hours))
        ].copy()
        pred_df = apply_residual_layer(pred_df, future_weather, PLANTS)
        pred_df = apply_physics_constraints(pred_df, future_weather, PLANTS)
        pred_df = generate_explanations(pred_df, use_api=False)
        all_plant_forecasts.append(pred_df)

    if not all_plant_forecasts:
        return []

    # Merge and aggregate by timestamp
    merged = all_plant_forecasts[0][["timestamp"]].copy()
    for i, df in enumerate(all_plant_forecasts):
        merged = merged.merge(df[["timestamp", "final_forecast_MW", "confidence_lower", "confidence_upper", "plant_id", "explanation"]],
                              on="timestamp", how="outer", suffixes=("", f"_{i}"))

    # Sum forecasts per timestamp
    sum_cols = [c for c in merged.columns if c.startswith("final_forecast_MW")]
    lower_cols = [c for c in merged.columns if c.startswith("confidence_lower")]
    upper_cols = [c for c in merged.columns if c.startswith("confidence_upper")]

    merged["aggregated_forecast_MW"] = merged[sum_cols].sum(axis=1)
    merged["confidence_lower"] = merged[lower_cols].sum(axis=1)
    merged["confidence_upper"] = merged[upper_cols].sum(axis=1)

    results = []
    for _, row in merged.iterrows():
        breakdown = []
        for df in all_plant_forecasts:
            sub = df[df["timestamp"] == row["timestamp"]]
            if not sub.empty:
                s = sub.iloc[0]
                breakdown.append({
                    "plant_id": s["plant_id"],
                    "forecast_MW": round(float(s["final_forecast_MW"]), 1),
                    "explanation": s.get("explanation", "")[:60]
                })
        results.append(ClusterForecastResponse(
            cluster_name="Karnataka Renewable Cluster",
            timestamp=str(row["timestamp"]),
            aggregated_forecast_MW=round(float(row["aggregated_forecast_MW"]), 1),
            confidence_lower=round(float(row["confidence_lower"]), 1),
            confidence_upper=round(float(row["confidence_upper"]), 1),
            plant_breakdown=breakdown,
            key_drivers=f"{len(breakdown)} plants aggregated"
        ))
    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
