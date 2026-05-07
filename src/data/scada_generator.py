"""
Synthetic SCADA Generator v2 — Realistic Generation Based on NASA POWER GHI
Uses real satellite-derived irradiance to build physically realistic solar output.
Wind uses Open-Meteo real wind speeds with proper power curves.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path

PLANTS = [
    {"plant_id": "SOL_PAVAGADA_100", "type": "solar", "capacity_mw": 100.0, "lat": 14.25, "lon": 77.28},
    {"plant_id": "SOL_KOPPAL_50",    "type": "solar", "capacity_mw": 50.0,  "lat": 15.35, "lon": 76.15},
    {"plant_id": "SOL_RAICHUR_200",  "type": "solar", "capacity_mw": 200.0, "lat": 16.21, "lon": 77.35},
    {"plant_id": "WIND_CHITRADURGA_80", "type": "wind", "capacity_mw": 80.0, "lat": 14.23, "lon": 76.40,
     "turbine_rated_power_mw": 2.5, "cut_in_ms": 3.5, "rated_wind_ms": 12.0, "cut_out_ms": 25.0, "n_turbines": 32},
    {"plant_id": "WIND_HASSAN_150", "type": "wind", "capacity_mw": 150.0, "lat": 13.00, "lon": 76.10,
     "turbine_rated_power_mw": 3.0, "cut_in_ms": 3.0, "rated_wind_ms": 11.5, "cut_out_ms": 25.0, "n_turbines": 50},
]

# Inject 5 weather anomaly events
ANOMALIES = [
    {"day": "2025-02-18", "hour": 14, "type": "cloud_spike", "intensity": 0.65, "plant_id": "SOL_PAVAGADA_100"},
    {"day": "2025-03-05", "hour": 11, "type": "dust_storm",  "intensity": 0.45, "plant_id": "SOL_RAICHUR_200"},
    {"day": "2025-01-28", "hour": 15, "type": "wind_ramp",   "intensity": 0.70, "plant_id": "WIND_CHITRADURGA_80"},
    {"day": "2025-02-10", "hour": 10, "type": "cloud_band",  "intensity": 0.55, "plant_id": "SOL_KOPPAL_50"},
    {"day": "2025-03-20", "hour": 18, "type": "wind_lull",   "intensity": 0.60, "plant_id": "WIND_HASSAN_150"},
]


def wind_power_curve(wind_speed, cut_in, rated, cut_out, rated_power_mw):
    if wind_speed < cut_in or wind_speed >= cut_out:
        return 0.0
    if wind_speed >= rated:
        return rated_power_mw
    ratio = (wind_speed - cut_in) / (rated - cut_in)
    return rated_power_mw * (ratio ** 3)


def generate_realistic_scada(nasa_ghi_path="data/weather/nasa_power_ghi.parquet",
                             weather_path="data/weather/weather_all.parquet",
                             output_dir="data/synthetic_scada",
                             seed=42):
    rng = np.random.default_rng(seed)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    nasa = pd.read_parquet(nasa_ghi_path)
    weather = pd.read_parquet(weather_path)
    nasa["timestamp"] = pd.to_datetime(nasa["timestamp"]).dt.tz_localize(None)
    weather["timestamp"] = pd.to_datetime(weather["timestamp"]).dt.tz_localize(None)

    all_records = []

    for plant in PLANTS:
        pid = plant["plant_id"]
        nasa_plant = nasa[nasa["plant_id"] == pid].copy().sort_values("timestamp")
        weather_plant = weather[weather["plant_id"] == pid].copy().sort_values("timestamp")
        
        if nasa_plant.empty:
            continue

        if plant["type"] == "solar":
            capacity = plant["capacity_mw"]
            for _, row in nasa_plant.iterrows():
                ts = row["timestamp"]
                ghi = row["ghi_nasa"]
                
                # Derating factors
                # Module efficiency ~18%, system losses ~15%, so net ~15.3%
                # 1 kW panel @ 1000 W/m2 → ~153 W AC output
                # But capacity already accounts for DC/AC ratio
                # Use simpler: capacity_factor = (ghi / 1000) * performance_ratio
                # Performance ratio for Indian utility solar ~0.78–0.82
                pr = rng.uniform(0.78, 0.82)
                
                # Temperature derating: -0.35%/°C above 25°C
                temp = 28 + 5 * np.sin(2 * np.pi * ts.dayofyear / 365)  # rough estimate
                temp_loss = max(0, 0.0035 * (temp - 25))
                
                base = capacity * (ghi / 1000.0) * pr * (1 - temp_loss)
                
                # Add noise
                noise = rng.normal(0, capacity * 0.015)
                gen = max(0.0, min(base + noise, capacity))
                
                all_records.append({
                    "timestamp": ts,
                    "plant_id": pid,
                    "generation_MW": round(gen, 3),
                    "capacity_MW": capacity,
                })
        else:
            # Wind
            capacity = plant["capacity_mw"]
            for _, row in weather_plant.iterrows():
                ts = row["timestamp"]
                ws = row.get("wind_speed_10m", 6.0)
                if pd.isna(ws):
                    ws = 0
                ws = max(0, ws + rng.normal(0, 0.3))  # add turbulence
                
                per_turbine = wind_power_curve(
                    ws, plant["cut_in_ms"], plant["rated_wind_ms"],
                    plant["cut_out_ms"], plant["turbine_rated_power_mw"]
                )
                base = per_turbine * plant["n_turbines"]
                availability = rng.uniform(0.94, 0.99)  # 94-99% availability
                base *= availability
                
                # Monsoon boost
                if 6 <= ts.month <= 9:
                    base *= rng.uniform(1.05, 1.20)
                
                noise = rng.normal(0, capacity * 0.02)
                gen = max(0.0, min(base + noise, capacity))
                
                all_records.append({
                    "timestamp": ts,
                    "plant_id": pid,
                    "generation_MW": round(gen, 3),
                    "capacity_MW": capacity,
                })

    df_all = pd.DataFrame(all_records)
    df_all = df_all.sort_values(["plant_id", "timestamp"]).reset_index(drop=True)

    # Inject anomalies
    for anom in ANOMALIES:
        anom_ts = pd.to_datetime(anom["day"]) + timedelta(hours=anom["hour"])
        mask = (df_all["plant_id"] == anom["plant_id"]) & (df_all["timestamp"] == anom_ts)
        if mask.any():
            idx = df_all.loc[mask].index[0]
            old_val = df_all.at[idx, "generation_MW"]
            if anom["type"] in ("cloud_spike", "dust_storm", "cloud_band"):
                new_val = old_val * (1.0 - anom["intensity"])
            elif anom["type"] == "wind_ramp":
                new_val = min(old_val * (1.0 + anom["intensity"]), df_all.at[idx, "capacity_MW"])
            elif anom["type"] == "wind_lull":
                new_val = old_val * (1.0 - anom["intensity"])
            else:
                new_val = old_val
            df_all.at[idx, "generation_MW"] = round(new_val, 3)

    csv_path = output_path / "synthetic_scada.csv"
    df_all.to_csv(csv_path, index=False)
    
    meta = {"plants": PLANTS, "anomalies": ANOMALIES, "seed": seed, "source": "NASA_POWER_GHI_BASED"}
    with open(output_path / "scada_metadata.json", "w") as f:
        json.dump(meta, f, indent=2, default=str)

    print(f"Generated {len(df_all)} realistic records across {len(PLANTS)} plants.")
    print(f"Saved to {csv_path}")
    
    # Quick validation
    for plant in PLANTS:
        pid = plant["plant_id"]
        sub = df_all[df_all["plant_id"] == pid]
        print(f"  {pid}: max={sub['generation_MW'].max():.1f} MW, mean={sub['generation_MW'].mean():.1f} MW")
    
    return df_all


if __name__ == "__main__":
    generate_realistic_scada()
