"""
Residual Adjustment Layer
Uses satellite cloud fraction (from IR thresholding) to adjust baseline forecast.
"""
import numpy as np
import pandas as pd
from pathlib import Path

from pipeline.physics_constraints import wind_power_curve_mw


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


def compute_residual_adjustment(cloud_fraction, plant_type, capacity_mw, baseline_mw):
    """
    Rule-based residual based on cloud fraction.
    No training required. Coefficients are physics-inspired.
    """
    if plant_type != "solar":
        return 0.0  # Wind residual handled differently or ignored in prototype
    if cloud_fraction < 0.2:
        return 0.0
    elif cloud_fraction < 0.5:
        attenuation = cloud_fraction * 0.25
    elif cloud_fraction < 0.75:
        attenuation = cloud_fraction * 0.35
    else:
        attenuation = cloud_fraction * 0.43
    residual = -attenuation * baseline_mw
    return residual


def compute_wind_adjustment(wind_speed, plant_meta, baseline_mw, availability=0.965):
    """
    Use the weather-driven turbine curve as the primary wind correction signal.
    """
    if pd.isna(wind_speed):
        return 0.0, baseline_mw

    per_turbine = wind_power_curve_mw(
        wind_speed,
        plant_meta.get("cut_in_ms", 3.5),
        plant_meta.get("rated_wind_ms", 12.0),
        plant_meta.get("cut_out_ms", 25.0),
        plant_meta.get("turbine_rated_power_mw", 2.5),
    )
    wind_based_mw = per_turbine * plant_meta.get("n_turbines", 1) * availability
    return wind_based_mw - baseline_mw, wind_based_mw


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
    weather_sub = weather_df[["plant_id", "timestamp", "cloud_cover", "wind_speed_10m"]].copy()
    weather_sub["timestamp"] = pd.to_datetime(weather_sub["timestamp"]).dt.tz_localize(None)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df = df.merge(weather_sub, on=["plant_id", "timestamp"], how="left")
    df["cloud_fraction"] = (df["cloud_cover"].fillna(0) / 100.0).clip(0, 1)

    # Map plant_id to type and capacity
    meta_map = {p["plant_id"]: p for p in plant_meta}
    df["plant_type"] = df["plant_id"].map(lambda x: meta_map.get(x, {}).get("type", "solar"))
    df["capacity_mw"] = df["plant_id"].map(lambda x: meta_map.get(x, {}).get("capacity_mw", 100.0))

    def compute_row(row):
        baseline = row.get("predictions", row.get("forecast_MW", 0.0))
        if row["plant_type"] == "wind":
            plant = meta_map.get(row["plant_id"], {})
            residual, wind_based_mw = compute_wind_adjustment(
                row.get("wind_speed_10m"),
                plant,
                baseline,
            )
            return pd.Series({"residual_MW": residual, "wind_based_MW": wind_based_mw})
        residual = compute_residual_adjustment(
            row["cloud_fraction"], row["plant_type"], row["capacity_mw"], baseline
        )
        return pd.Series({"residual_MW": residual, "wind_based_MW": np.nan})

    df[["residual_MW", "wind_based_MW"]] = df.apply(compute_row, axis=1)
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
