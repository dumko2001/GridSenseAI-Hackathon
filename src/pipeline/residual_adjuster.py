"""
Residual Adjustment Layer
Uses satellite cloud fraction (from IR thresholding) to adjust baseline forecast.
"""
import numpy as np
import pandas as pd
from pathlib import Path


def compute_cloud_fraction_from_ir(ir_image_kelvin, threshold_k=230.0):
    """
    Simple IR threshold cloud mask.
    ir_image_kelvin: 2D numpy array of brightness temperature.
    Clouds are colder than threshold.
    Returns cloud_fraction (0.0 to 1.0).
    """
    if ir_image_kelvin is None or ir_image_kelvin.size == 0:
        return 0.0
    cloud_pixels = np.sum(ir_image_kelvin < threshold_k)
    total_pixels = ir_image_kelvin.size
    return float(cloud_pixels / total_pixels)


def compute_residual_adjustment(cloud_fraction, plant_type, capacity_mw):
    """
    Rule-based residual based on cloud fraction.
    No training required. Coefficients are physics-inspired.
    """
    if plant_type != "solar":
        return 0.0  # Wind residual handled differently or ignored in prototype
    if cloud_fraction < 0.2:
        return 0.0
    elif cloud_fraction < 0.5:
        attenuation = cloud_fraction * 0.5
    elif cloud_fraction < 0.75:
        attenuation = cloud_fraction * 0.65
    else:
        attenuation = cloud_fraction * 0.75
    residual = -attenuation * capacity_mw
    return residual


def apply_residual_layer(baseline_forecast_df, weather_df, plant_meta):
    """
    Merge baseline forecast with weather-based cloud fraction estimates.
    Since we don't have real-time MOSDAC images for every hour in the prototype,
    we use Open-Meteo cloud_cover as a proxy for satellite cloud fraction,
    but the architecture slot is ready for real IR imagery.
    """
    df = baseline_forecast_df.copy()
    # Merge with weather on timestamp and plant_id
    # Use Open-Meteo cloud_cover (0-100%) as proxy for now
    weather_sub = weather_df[["plant_id", "timestamp", "cloud_cover"]].copy()
    weather_sub["timestamp"] = pd.to_datetime(weather_sub["timestamp"]).dt.tz_localize(None)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df = df.merge(weather_sub, on=["plant_id", "timestamp"], how="left")
    df["cloud_fraction"] = (df["cloud_cover"].fillna(0) / 100.0).clip(0, 1)

    # Map plant_id to type and capacity
    meta_map = {p["plant_id"]: p for p in plant_meta}
    df["plant_type"] = df["plant_id"].map(lambda x: meta_map.get(x, {}).get("type", "solar"))
    df["capacity_mw"] = df["plant_id"].map(lambda x: meta_map.get(x, {}).get("capacity_mw", 100.0))

    df["residual_MW"] = df.apply(
        lambda row: compute_residual_adjustment(
            row["cloud_fraction"], row["plant_type"], row["capacity_mw"]
        ), axis=1
    )
    # Add residual to baseline prediction
    if "predictions" in df.columns:
        df["pre_physics_MW"] = df["predictions"] + df["residual_MW"]
    else:
        df["pre_physics_MW"] = df.get("forecast_MW", 0) + df["residual_MW"]
    return df


if __name__ == "__main__":
    # Quick test
    from src.data.scada_generator import PLANTS
    bf = pd.read_parquet("models/baseline/baseline_forecasts.parquet")
    wf = pd.read_parquet("data/weather/weather_all.parquet")
    out = apply_residual_layer(bf, wf, PLANTS)
    print(out[["plant_id", "timestamp", "predictions", "cloud_fraction", "residual_MW", "pre_physics_MW"]].head(10))
