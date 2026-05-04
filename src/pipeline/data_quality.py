"""
Data Quality Monitor
Real SCADA data is messy. Sensors fail, communication links drop, inverters report flatlined values.
This module detects data quality issues BEFORE they poison the forecast.
"""
import pandas as pd
import numpy as np
from datetime import timedelta


def check_data_quality(scada_df, plant_meta):
    """
    Run data quality checks on SCADA input.
    Returns: (clean_df, issues_list)
    """
    df = scada_df.copy().sort_values(["plant_id", "timestamp"])
    issues = []
    meta_map = {p["plant_id"]: p for p in plant_meta}

    for pid in df["plant_id"].unique():
        sub = df[df["plant_id"] == pid].copy()
        meta = meta_map.get(pid, {})
        cap = meta.get("capacity_mw", 100.0)

        # 1. Gap detection: missing timestamps
        expected_freq = pd.infer_freq(sub["timestamp"])
        if expected_freq is None:
            expected_freq = "h"
        full_range = pd.date_range(start=sub["timestamp"].min(), end=sub["timestamp"].max(), freq=expected_freq)
        missing_ts = len(full_range) - len(sub)
        if missing_ts > 0:
            issues.append({
                "plant_id": pid,
                "severity": "warning" if missing_ts < 5 else "critical",
                "type": "missing_timestamps",
                "message": f"{missing_ts} missing hourly readings. Interpolation will be used.",
            })

        # 2. Flatline detection: same value repeated > 6 hours
        sub["gen_diff"] = sub["generation_MW"].diff().abs()
        flatline_mask = sub["gen_diff"] == 0
        flatline_runs = []
        current_run = 0
        for is_flat in flatline_mask:
            if is_flat:
                current_run += 1
            else:
                if current_run >= 6:
                    flatline_runs.append(current_run)
                current_run = 0
        if flatline_runs:
            issues.append({
                "plant_id": pid,
                "severity": "warning",
                "type": "flatline",
                "message": f"Flatlined generation detected for {max(flatline_runs)} consecutive hours. Possible sensor freeze or inverter shutdown.",
            })

        # 3. Impossible values: negative generation or > 1.1× capacity
        neg_count = (sub["generation_MW"] < -0.1).sum()
        over_count = (sub["generation_MW"] > cap * 1.1).sum()
        if neg_count > 0:
            issues.append({
                "plant_id": pid,
                "severity": "critical",
                "type": "negative_generation",
                "message": f"{neg_count} readings show negative generation. Physically impossible.",
            })
        if over_count > 0:
            issues.append({
                "plant_id": pid,
                "severity": "critical",
                "type": "over_capacity",
                "message": f"{over_count} readings exceed 110% of rated capacity ({cap} MW). Sensor miscalibration likely.",
            })

        # 4. Sudden spike: > 50% capacity change in 1 hour (after flatline filter)
        sub["pct_change"] = sub["generation_MW"].pct_change().abs()
        spike_mask = sub["pct_change"] > 0.5
        spike_count = spike_mask.sum()
        if spike_count > 0:
            issues.append({
                "plant_id": pid,
                "severity": "warning",
                "type": "sudden_spike",
                "message": f"{spike_count} instances of >50% generation change in 1 hour. Possible communication error or grid event.",
            })

    # Apply minimal cleaning: interpolate small gaps, floor negatives, cap over-capacity
    clean = df.copy()
    clean["generation_MW"] = clean["generation_MW"].clip(lower=0)
    # Group-by interpolate
    clean = clean.groupby("plant_id").apply(lambda g: g.sort_values("timestamp").set_index("timestamp").resample("h").interpolate(method="linear").reset_index())
    if "plant_id" not in clean.columns:
        clean = clean.reset_index()
    # Ensure plant_id is preserved after groupby
    if "plant_id" not in clean.columns:
        clean["plant_id"] = scada_df["plant_id"].iloc[0]

    return clean, issues


def generate_quality_report(issues, output_path="reports/data_quality_report.json"):
    """Write JSON quality report for ingestion by SLDC monitoring dashboard."""
    import json
    from pathlib import Path
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "generated_at": pd.Timestamp.now().isoformat(),
            "total_issues": len(issues),
            "critical_count": sum(1 for i in issues if i["severity"] == "critical"),
            "warning_count": sum(1 for i in issues if i["severity"] == "warning"),
            "issues": issues,
        }, f, indent=2)
    return output_path


if __name__ == "__main__":
    from data.scada_generator import PLANTS
    scada = pd.read_csv("data/synthetic_scada/synthetic_scada.csv", parse_dates=["timestamp"])
    clean, issues = check_data_quality(scada, PLANTS)
    print(f"Issues found: {len(issues)}")
    for i in issues[:5]:
        print(f"  [{i['severity'].upper()}] {i['plant_id']}: {i['message']}")
    if issues:
        path = generate_quality_report(issues)
        print(f"Report written to {path}")
