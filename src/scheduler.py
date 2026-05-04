"""
Auto-Scheduler for SLDC Operations
Runs forecasts automatically at scheduled times and writes Excel-ready CSV reports
to a directory that SLDC operators can open directly.

Real SLDC workflow:
1. At 06:00 IST: Run day-ahead forecast (24h) → write to /reports/day_ahead_YYYYMMDD.csv
2. At 12:00 IST: Run intra-day update (12h) → write to /reports/intraday_YYYYMMDD.csv
3. Operator opens CSV in Excel at 06:15 IST, sees forecast + confidence + explanations
4. No Python, no dashboard, no clicking — just a file in a shared folder

This is how government offices actually work.
"""
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data.scada_generator import PLANTS
from pipeline.baseline_forecaster import load_pipeline, forecast_baseline
from pipeline.residual_adjuster import apply_residual_layer
from pipeline.physics_constraints import apply_physics_constraints
from pipeline.explainability import generate_explanations
from pipeline.data_quality import check_data_quality


def run_scheduled_forecast(plant_ids, prediction_hours=24, report_dir="reports",
                           report_prefix="forecast", include_explanations=True):
    """
    Run forecast for multiple plants and write a single consolidated CSV report.
    Designed to be called by cron at 06:00 and 12:00 IST.
    """
    pipeline = load_pipeline()
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    scada = pd.read_csv("data/synthetic_scada/synthetic_scada.csv", parse_dates=["timestamp"])
    weather = pd.read_parquet("data/weather/weather_all.parquet")
    scada["timestamp"] = pd.to_datetime(scada["timestamp"]).dt.tz_localize(None)
    weather["timestamp"] = pd.to_datetime(weather["timestamp"]).dt.tz_localize(None)

    # Data quality check first
    clean_scada, quality_issues = check_data_quality(scada, PLANTS)
    if quality_issues:
        print(f"⚠️  Data quality issues detected: {len(quality_issues)}")
        for issue in quality_issues:
            print(f"   [{issue['severity'].upper()}] {issue['plant_id']}: {issue['message']}")

    all_results = []
    for pid in plant_ids:
        ctx = clean_scada[clean_scada["plant_id"] == pid].sort_values("timestamp").tail(168)
        if len(ctx) < prediction_hours * 2:
            print(f"Skipping {pid}: insufficient context ({len(ctx)} hours)")
            continue

        pred_df = forecast_baseline(pipeline, ctx, prediction_length=prediction_hours)
        pred_df["plant_id"] = pid
        if "0.1" in pred_df.columns:
            pred_df["confidence_lower"] = pred_df["0.1"]
        if "0.9" in pred_df.columns:
            pred_df["confidence_upper"] = pred_df["0.9"]

        last_ts = ctx["timestamp"].max()
        future_weather = weather[
            (weather["plant_id"] == pid) &
            (weather["timestamp"] > last_ts) &
            (weather["timestamp"] <= last_ts + pd.Timedelta(hours=prediction_hours))
        ].copy()

        pred_df = apply_residual_layer(pred_df, future_weather, PLANTS)
        pred_df = apply_physics_constraints(pred_df, future_weather, PLANTS)
        pred_df = generate_explanations(pred_df)

        for _, row in pred_df.iterrows():
            all_results.append({
                "plant_id": pid,
                "plant_name": pid,
                "timestamp": row["timestamp"],
                "forecast_MW": round(float(row.get("final_forecast_MW", row.get("predictions", 0))), 1),
                "confidence_lower_MW": round(float(row.get("confidence_lower", 0)), 1),
                "confidence_upper_MW": round(float(row.get("confidence_upper", 0)), 1),
                "uncertainty_band_MW": round(float(row.get("confidence_upper", 0) - row.get("confidence_lower", 0)), 1),
                "was_clamped": bool(row.get("was_clamped", False)),
                "clamp_reason": row.get("clamp_reason", ""),
                "explanation": row.get("explanation", "") if include_explanations else "",
                "generated_at": datetime.now(),
            })

    if not all_results:
        print("No forecasts generated.")
        return None

    report_df = pd.DataFrame(all_results)
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{report_prefix}_{date_str}.csv"
    filepath = report_dir / filename
    report_df.to_csv(filepath, index=False)
    print(f"✅ Report written: {filepath} ({len(report_df)} rows)")

    # Also write a summary JSON for dashboard ingestion
    summary = {
        "report_time": datetime.now().isoformat(),
        "forecast_horizon_hours": prediction_hours,
        "plants_forecasted": len(plant_ids),
        "total_rows": len(report_df),
        "file": str(filepath),
    }
    summary_path = report_dir / f"{report_prefix}_{date_str}_summary.json"
    import json
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    return filepath


def run_day_ahead():
    """Run at 06:00 IST for next 24 hours."""
    plant_ids = [p["plant_id"] for p in PLANTS]
    return run_scheduled_forecast(plant_ids, prediction_hours=24, report_prefix="day_ahead")


def run_intraday():
    """Run at 12:00 IST for next 12 hours."""
    plant_ids = [p["plant_id"] for p in PLANTS]
    return run_scheduled_forecast(plant_ids, prediction_hours=12, report_prefix="intraday")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["day_ahead", "intraday", "custom"], default="day_ahead")
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()

    if args.mode == "day_ahead":
        run_day_ahead()
    elif args.mode == "intraday":
        run_intraday()
    else:
        plant_ids = [p["plant_id"] for p in PLANTS]
        run_scheduled_forecast(plant_ids, prediction_hours=args.hours, report_prefix="custom")
