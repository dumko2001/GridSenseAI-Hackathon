"""
Baseline Forecaster: Chronos-Bolt-Small zero-shot inference.
Trains/fine-tunes nothing. Loads pretrained model and forecasts.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import warnings

try:
    from chronos import ChronosBoltPipeline
except ImportError as e:
    warnings.warn(f"Chronos not available: {e}")
    ChronosBoltPipeline = None

# Default model ID on HuggingFace
MODEL_ID = "amazon/chronos-bolt-small"


def load_pipeline(model_id=MODEL_ID, device="cpu"):
    """Load pretrained Chronos-Bolt pipeline."""
    if ChronosBoltPipeline is None:
        raise RuntimeError("chronos-forecasting not installed.")
    print(f"Loading Chronos-Bolt model: {model_id} ...")
    pipeline = ChronosBoltPipeline.from_pretrained(model_id, device_map=device)
    print("Model loaded.")
    return pipeline


def prepare_chronos_df(scada_df, weather_df):
    """
    Merge SCADA and weather. Chronos-Bolt here runs univariate on generation_MW.
    Weather covariates are used later in the residual layer.
    """
    scada = scada_df.copy()
    weather = weather_df.copy()
    scada["timestamp"] = pd.to_datetime(scada["timestamp"]).dt.tz_localize(None)
    weather["timestamp"] = pd.to_datetime(weather["timestamp"]).dt.tz_localize(None)
    df = scada.merge(weather, on=["plant_id", "timestamp"], how="left")
    covariates = ["cloud_cover", "wind_speed_10m", "ghi", "temperature_2m"]
    for col in covariates:
        if col in df.columns:
            df[col] = df[col].ffill().bfill()
        else:
            df[col] = 0.0
    return df


def forecast_baseline(pipeline, context_df, prediction_length=24):
    """
    Run zero-shot univariate forecast with Chronos-Bolt.
    context_df must have id_column, timestamp_column, target.
    """
    pred_df = pipeline.predict_df(
        context_df,
        prediction_length=prediction_length,
        quantile_levels=[0.1, 0.5, 0.9],
        id_column="plant_id",
        timestamp_column="timestamp",
        target="generation_MW",
    )
    return pred_df


def run_baseline_forecast(scada_path="data/synthetic_scada/synthetic_scada.csv",
                          weather_path="data/weather/weather_all.parquet",
                          output_dir="models/baseline",
                          prediction_length=24,
                          test_days=14):
    """
    End-to-end baseline forecast for all plants.
    Splits last test_days as hold-out for evaluation.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scada = pd.read_csv(scada_path, parse_dates=["timestamp"])
    weather = pd.read_parquet(weather_path)

    df = prepare_chronos_df(scada, weather)

    # Determine split point (hold out last test_days)
    max_ts = df["timestamp"].max()
    split_ts = max_ts - pd.Timedelta(days=test_days)

    context_df = df[df["timestamp"] <= split_ts].copy()
    # For each plant, create future_df with covariates for the forecast window
    plants = df["plant_id"].unique()

    pipeline = load_pipeline()

    all_forecasts = []
    all_actuals = []

    for plant in plants:
        ctx = context_df[context_df["plant_id"] == plant].copy()
        if len(ctx) < prediction_length * 2:
            continue

        # Actuals for evaluation (next prediction_length hours)
        future = df[
            (df["plant_id"] == plant) &
            (df["timestamp"] > split_ts) &
            (df["timestamp"] <= split_ts + pd.Timedelta(hours=prediction_length))
        ].copy()

        if len(future) < prediction_length:
            continue

        pred = forecast_baseline(pipeline, ctx, prediction_length=prediction_length)
        pred["plant_id"] = plant
        all_forecasts.append(pred)

        actual = future[["timestamp", "generation_MW"]].copy()
        actual["plant_id"] = plant
        all_actuals.append(actual)

    forecasts = pd.concat(all_forecasts, ignore_index=True)
    actuals = pd.concat(all_actuals, ignore_index=True)

    # Save
    forecasts.to_parquet(output_dir / "baseline_forecasts.parquet", index=False)
    actuals.to_parquet(output_dir / "baseline_actuals.parquet", index=False)

    # Compute metrics
    merged = forecasts.merge(actuals, on=["plant_id", "timestamp"], how="inner")
    if not merged.empty and "predictions" in merged.columns:
        mae = np.mean(np.abs(merged["predictions"] - merged["generation_MW"]))
        rmse = np.sqrt(np.mean((merged["predictions"] - merged["generation_MW"]) ** 2))
        mape = np.mean(np.abs((merged["predictions"] - merged["generation_MW"]) / merged["generation_MW"].clip(lower=1))) * 100

        # Naive persistence baseline: yesterday same hour (use full scada for shift)
        full_scada = scada.copy()
        full_scada["timestamp"] = pd.to_datetime(full_scada["timestamp"]).dt.tz_localize(None)
        full_scada = full_scada.sort_values(["plant_id", "timestamp"])
        full_scada["predictions"] = full_scada.groupby("plant_id")["generation_MW"].shift(24)
        pers_merged = full_scada.merge(actuals[["plant_id", "timestamp", "generation_MW"]], on=["plant_id", "timestamp"], how="inner", suffixes=("", "_actual"))
        pers_merged = pers_merged.dropna(subset=["predictions"])
        if not pers_merged.empty:
            pers_rmse = np.sqrt(np.mean((pers_merged["predictions"] - pers_merged["generation_MW"]) ** 2))
        else:
            pers_rmse = 9999.0  # fallback

        metrics = {
            "mae": float(mae),
            "rmse": float(rmse),
            "mape": float(mape),
            "persistence_rmse": float(pers_rmse),
            "improvement_vs_persistence": float((1 - rmse / pers_rmse) * 100) if pers_rmse > 0 else 0.0,
        }
        print(f"Baseline metrics: {metrics}")
        with open(output_dir / "metrics.pkl", "wb") as f:
            pickle.dump(metrics, f)
    else:
        metrics = {}
        print("Could not compute metrics (check forecast columns).")

    return forecasts, actuals, metrics


if __name__ == "__main__":
    run_baseline_forecast()
