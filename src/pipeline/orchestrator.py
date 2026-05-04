"""
End-to-End Pipeline Orchestrator
Runs the full GridSense AI pipeline in one command.
"""
import pandas as pd
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data.scada_generator import PLANTS
from pipeline.baseline_forecaster import load_pipeline, forecast_baseline
from pipeline.residual_adjuster import apply_residual_layer
from pipeline.physics_constraints import apply_physics_constraints
from pipeline.explainability import generate_explanations


def run_full_pipeline(plant_id: str, forecast_timestamp: str = None, prediction_length: int = 24):
    """
    Run full pipeline for a single plant at a given time.
    If forecast_timestamp is None, uses the latest available context.
    """
    pipeline = load_pipeline()

    scada = pd.read_csv("data/synthetic_scada/synthetic_scada.csv", parse_dates=["timestamp"])
    weather = pd.read_parquet("data/weather/weather_all.parquet")
    scada["timestamp"] = pd.to_datetime(scada["timestamp"]).dt.tz_localize(None)
    weather["timestamp"] = pd.to_datetime(weather["timestamp"]).dt.tz_localize(None)

    ctx = scada[scada["plant_id"] == plant_id].copy().sort_values("timestamp")
    if forecast_timestamp:
        ts = pd.to_datetime(forecast_timestamp)
        ctx = ctx[ctx["timestamp"] <= ts]
    else:
        ts = ctx["timestamp"].max()

    if len(ctx) < prediction_length * 2:
        raise ValueError(f"Insufficient context for {plant_id}. Need {prediction_length*2} hours, got {len(ctx)}.")

    # Baseline
    pred_df = forecast_baseline(pipeline, ctx, prediction_length=prediction_length)
    pred_df["plant_id"] = plant_id

    # Future weather for residual/physics
    future_weather = weather[
        (weather["plant_id"] == plant_id) &
        (weather["timestamp"] > ts) &
        (weather["timestamp"] <= ts + pd.Timedelta(hours=prediction_length))
    ].copy()

    # Residual
    pred_df = apply_residual_layer(pred_df, future_weather, PLANTS)
    # Physics
    pred_df = apply_physics_constraints(pred_df, future_weather, PLANTS)
    # Explainability (100% offline template-based)
    pred_df = generate_explanations(pred_df)

    return pred_df


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--plant", default="SOL_PAVAGADA_100")
    parser.add_argument("--timestamp", default=None)
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()

    out = run_full_pipeline(args.plant, args.timestamp, args.hours)
    print(out[["plant_id", "timestamp", "predictions", "residual_MW", "final_forecast_MW", "explanation"]].head())
