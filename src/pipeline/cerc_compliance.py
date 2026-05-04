"""
CERC Regulatory Compliance Checker
India's Central Electricity Regulatory Commission (CERC) mandates
forecasting accuracy limits for renewable generators.

Key regulations (CERC Terms and Conditions for Tariff, 2020):
- Solar: Forecast error > 15% (RMSE) attracts DSM penalties
- Wind: Forecast error > 12% (RMSE) attracts DSM penalties
- Deviation Settlement Mechanism (DSM) charges:
  - Up to 15% deviation: no charge
  - 15-25% deviation: charges at base rate
  - >25% deviation: 2× base rate

This module benchmarks our forecast against these regulatory limits.
"""
import numpy as np
import pandas as pd


# CERC-mandated accuracy thresholds (% of installed capacity)
CERC_LIMITS = {
    "solar": 0.15,   # 15% RMSE of capacity
    "wind": 0.12,    # 12% RMSE of capacity
}


def compute_cerc_metrics(forecast_df, actual_df, plant_meta):
    """
    Compute CERC-compliant accuracy metrics.
    forecast_df: columns [plant_id, timestamp, forecast_MW]
    actual_df:   columns [plant_id, timestamp, generation_MW]
    Returns: dict with compliance status per plant
    """
    merged = forecast_df.merge(actual_df, on=["plant_id", "timestamp"], how="inner")
    if merged.empty:
        return {}

    meta_map = {p["plant_id"]: p for p in plant_meta}
    results = []

    for pid in merged["plant_id"].unique():
        sub = merged[merged["plant_id"] == pid].copy()
        meta = meta_map.get(pid, {})
        ptype = meta.get("type", "solar")
        cap = meta.get("capacity_mw", 100.0)
        limit = CERC_LIMITS.get(ptype, 0.15)

        rmse = np.sqrt(np.mean((sub["forecast_MW"] - sub["generation_MW"]) ** 2))
        mae = np.mean(np.abs(sub["forecast_MW"] - sub["generation_MW"]))
        max_dev = np.max(np.abs(sub["forecast_MW"] - sub["generation_MW"]))

        rmse_pct = rmse / cap
        mae_pct = mae / cap
        max_dev_pct = max_dev / cap

        compliant = rmse_pct <= limit

        # DSM penalty estimate (simplified)
        deviations = np.abs(sub["forecast_MW"] - sub["generation_MW"]) / cap
        penalty_hours = np.sum(deviations > limit)
        # Approx ₹3-5 per unit DSM charge for solar, ₹2-3 for wind
        dsm_rate = 4.0 if ptype == "solar" else 2.5
        # Penalty = deviation_MWh × rate. Simplified: avg deviation × hours × rate
        avg_dev_mw = np.mean(np.abs(sub["forecast_MW"] - sub["generation_MW"]))
        estimated_daily_penalty = penalty_hours * avg_dev_mw * dsm_rate * 1000  # ₹

        results.append({
            "plant_id": pid,
            "plant_type": ptype,
            "capacity_mw": cap,
            "cerc_limit_pct": limit * 100,
            "rmse_mw": round(rmse, 2),
            "rmse_pct_of_cap": round(rmse_pct * 100, 2),
            "mae_mw": round(mae, 2),
            "mae_pct_of_cap": round(mae_pct * 100, 2),
            "max_deviation_mw": round(max_dev, 2),
            "max_deviation_pct": round(max_dev_pct * 100, 2),
            "cerc_compliant": bool(compliant),
            "estimated_daily_penalty_inr": round(estimated_daily_penalty, 0),
            "penalty_risk": "low" if rmse_pct < limit * 0.8 else ("medium" if rmse_pct < limit else "high"),
        })

    return results


def generate_cerc_report(metrics_list, output_path="reports/cerc_compliance_report.json"):
    """Write JSON compliance report."""
    import json
    from pathlib import Path
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    overall_compliant = all(m["cerc_compliant"] for m in metrics_list)
    total_penalty = sum(m["estimated_daily_penalty_inr"] for m in metrics_list)

    report = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "overall_compliant": overall_compliant,
        "total_estimated_daily_penalty_inr": total_penalty,
        "regulation": "CERC Terms and Conditions for Tariff (2020)",
        "plants": metrics_list,
    }
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    return report


if __name__ == "__main__":
    # Example: benchmark baseline forecasts against actuals
    from data.scada_generator import PLANTS
    forecasts = pd.read_parquet("models/baseline/baseline_forecasts.parquet")
    actuals = pd.read_parquet("models/baseline/baseline_actuals.parquet")

    if "predictions" in forecasts.columns:
        forecasts = forecasts.rename(columns={"predictions": "forecast_MW"})

    metrics = compute_cerc_metrics(forecasts, actuals, PLANTS)
    for m in metrics:
        status = "✅ COMPLIANT" if m["cerc_compliant"] else "❌ NON-COMPLIANT"
        print(f"{m['plant_id']}: {status} | RMSE {m['rmse_pct_of_cap']}% (limit {m['cerc_limit_pct']}%) | Penalty: ₹{m['estimated_daily_penalty_inr']}/day")
    if metrics:
        generate_cerc_report(metrics)
