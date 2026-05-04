"""
Physics Constraint Layer
Enforces real-world physical limits on generation forecasts.
No training. Pure rule-based clamping.
"""
import numpy as np
import pandas as pd


def clear_sky_ghi(hour, day_of_year, lat_deg):
    """Simple clear-sky GHI estimator (W/m^2)."""
    lat_rad = np.radians(lat_deg)
    decl = np.radians(23.45 * np.sin(np.radians((360 / 365) * (day_of_year - 81))))
    ha = np.radians(15 * (hour - 12))
    cz = np.sin(lat_rad) * np.sin(decl) + np.cos(lat_rad) * np.cos(decl) * np.cos(ha)
    cz = np.clip(cz, 0, 1)
    return 1000 * cz


def wind_power_curve_mw(wind_speed, cut_in, rated, cut_out, rated_power_mw):
    if wind_speed < cut_in or wind_speed >= cut_out:
        return 0.0
    if wind_speed >= rated:
        return rated_power_mw
    ratio = (wind_speed - cut_in) / (rated - cut_in)
    return rated_power_mw * (ratio ** 3)


def apply_physics_constraints(df, weather_df, plant_meta):
    """
    df must have: plant_id, timestamp, pre_physics_MW
    Returns df with final_forecast_MW, clamp_reason, was_clamped.
    """
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    weather_df = weather_df.copy()
    weather_df["timestamp"] = pd.to_datetime(weather_df["timestamp"]).dt.tz_localize(None)

    # Merge weather for wind speed / GHI
    df = df.merge(
        weather_df[["plant_id", "timestamp", "wind_speed_10m", "ghi", "temperature_2m"]],
        on=["plant_id", "timestamp"],
        how="left"
    )

    meta_map = {p["plant_id"]: p for p in plant_meta}

    results = []
    for _, row in df.iterrows():
        pid = row["plant_id"]
        meta = meta_map.get(pid, {})
        ptype = meta.get("type", "solar")
        cap = meta.get("capacity_mw", 100.0)
        val = row["pre_physics_MW"]
        clamp_reason = None
        was_clamped = False

        if ptype == "solar":
            # Clear-sky cap
            cs = clear_sky_ghi(row["timestamp"].hour, row["timestamp"].dayofyear, meta.get("lat", 14.0))
            # Simple derating: assume ~20% module efficiency, 80% system efficiency
            # cap in MW, cs in W/m2. Need plant area proxy: assume 5 m2/kW
            # So max MW = cs * (cap * 1000 kW * 5 m2/kW) / 1e6 * 0.2 * 0.8
            # Simplified: max MW ≈ cap * (cs / 1000) * 0.8
            max_solar = cap * (cs / 1000.0) * 0.8
            if val > max_solar:
                val = max_solar
                clamp_reason = f"Capped by clear-sky GHI limit ({cs:.0f} W/m2)"
                was_clamped = True
        else:
            # Wind
            ws = row.get("wind_speed_10m")
            if pd.isna(ws):
                # Weather data missing for this forecast timestamp — skip wind-specific physics,
                # only apply hard capacity cap and floor below
                pass
            else:
                per_turbine = wind_power_curve_mw(
                    ws,
                    meta.get("cut_in_ms", 3.5),
                    meta.get("rated_wind_ms", 12.0),
                    meta.get("cut_out_ms", 25.0),
                    meta.get("turbine_rated_power_mw", 2.5)
                )
                max_wind = per_turbine * meta.get("n_turbines", 1)
                if val > max_wind:
                    val = max_wind
                    clamp_reason = f"Capped by turbine power curve at {ws:.1f} m/s"
                    was_clamped = True
                if ws < meta.get("cut_in_ms", 3.5):
                    if val > 0:
                        val = 0.0
                        clamp_reason = f"Zeroed: wind {ws:.1f} m/s below cut-in"
                        was_clamped = True

        # Hard cap at plant capacity (ceiling)
        if val > cap:
            val = cap
            clamp_reason = "Capped at plant rated capacity"
            was_clamped = True

        # Floor at 0 MW — generation cannot be negative
        if val < 0:
            val = 0.0
            if not clamp_reason:
                clamp_reason = "Floored at 0 MW (generation cannot be negative)"
            was_clamped = True

        # Ramp rate limit (per plant historical 95th percentile ~15% capacity/hr)
        # For prototype we enforce forward-only; backward check would need prev value
        # We'll store the limit for downstream use
        max_ramp = cap * 0.25  # 25% per hour generous

        row_out = row.to_dict()
        row_out["final_forecast_MW"] = round(float(val), 3)
        row_out["clamp_reason"] = clamp_reason or ""
        row_out["was_clamped"] = bool(was_clamped)
        row_out["max_ramp_MW"] = max_ramp
        results.append(row_out)

    return pd.DataFrame(results)


if __name__ == "__main__":
    from src.data.scada_generator import PLANTS
    from src.pipeline.residual_adjuster import apply_residual_layer
    bf = pd.read_parquet("models/baseline/baseline_forecasts.parquet")
    wf = pd.read_parquet("data/weather/weather_all.parquet")
    res = apply_residual_layer(bf, wf, PLANTS)
    phy = apply_physics_constraints(res, wf, PLANTS)
    print(phy[["plant_id", "timestamp", "pre_physics_MW", "final_forecast_MW", "clamp_reason", "was_clamped"]].head(10))
