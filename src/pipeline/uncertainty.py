"""
Uncertainty post-processing for final forecast bands.
"""
from __future__ import annotations

import math

import pandas as pd


def apply_confidence_bands(df: pd.DataFrame, plant_meta) -> pd.DataFrame:
    """
    Align confidence bands with the final forecast after residual/physics updates.
    """
    out = df.copy()
    meta_map = {p["plant_id"]: p for p in plant_meta}

    lowers = []
    uppers = []

    for _, row in out.iterrows():
        meta = meta_map.get(row["plant_id"], {})
        cap = float(meta.get("capacity_mw", 100.0))
        plant_type = meta.get("type", "solar")

        center = float(row.get("final_forecast_MW", row.get("predictions", 0.0)))
        baseline = float(row.get("predictions", row.get("forecast_MW", center)))
        q10 = float(row.get("0.1", baseline * 0.9))
        q90 = float(row.get("0.9", baseline * 1.1))

        width = max(abs(baseline - q10), abs(q90 - baseline), cap * 0.02)
        volatility = 1.0

        if plant_type == "solar":
            cloud_fraction = float(row.get("cloud_fraction", 0.0) or 0.0)
            volatility += 0.45 * cloud_fraction
        else:
            ws = row.get("wind_speed_10m")
            if pd.isna(ws):
                volatility += 0.25
            else:
                ws = float(ws)
                cut_in = float(meta.get("cut_in_ms", 3.5))
                rated = float(meta.get("rated_wind_ms", 12.0))
                cut_out = float(meta.get("cut_out_ms", 25.0))
                if ws <= cut_in + 1.0 or ws >= cut_out - 2.0:
                    volatility += 0.4
                elif abs(ws - rated) <= 1.5:
                    volatility += 0.2
                else:
                    volatility += 0.08

        if row.get("was_clamped", False):
            volatility += 0.1

        width *= volatility
        lower = max(0.0, center - width)
        upper = min(cap, center + width)

        if math.isnan(lower):
            lower = 0.0
        if math.isnan(upper):
            upper = cap

        lower = min(lower, center)
        upper = max(upper, center)

        lowers.append(round(lower, 3))
        uppers.append(round(upper, 3))

    out["confidence_lower"] = lowers
    out["confidence_upper"] = uppers
    return out
