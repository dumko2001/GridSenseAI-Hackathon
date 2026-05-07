"""
GridSense AI - FastAPI Backend
Serves forecasts via REST API for SLDC integration.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from runtime_config import chdir_project_root, configure_runtime

configure_runtime()
chdir_project_root()

from dotenv import load_dotenv
load_dotenv()

import pickle
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import io

from data.scada_generator import PLANTS
from pipeline.baseline_forecaster import load_pipeline, forecast_baseline
from pipeline.residual_adjuster import apply_residual_layer
from pipeline.physics_constraints import apply_physics_constraints
from pipeline.uncertainty import apply_confidence_bands
from pipeline.explainability import SUPPORTED_LANGUAGES, generate_explanations
from pipeline.data_quality import check_data_quality, generate_quality_report
from pipeline.cerc_compliance import compute_cerc_metrics, generate_cerc_report
from pipeline.operator_override import OverrideRule, get_override_manager

app = FastAPI(title="GridSense AI Forecast API", version="0.1.0")

# Lazy-load model on first request
_pipeline = None

def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = load_pipeline()
    return _pipeline


class ForecastRequest(BaseModel):
    plant_id: str
    context_hours: int = 168  # 7 days history
    prediction_hours: int = 24
    forecast_timestamp: Optional[str] = None
    language: str = "en"


class ForecastResponse(BaseModel):
    plant_id: str
    timestamp: str
    forecast_MW: float
    confidence_lower: float
    confidence_upper: float
    explanation: str
    was_clamped: bool
    clamp_reason: Optional[str] = None
    drivers: dict


class ClusterForecastRequest(BaseModel):
    plant_ids: List[str]
    context_hours: int = 168
    prediction_hours: int = 24
    forecast_timestamp: Optional[str] = None
    language: str = "en"
    cluster_name: str = "Karnataka Renewable Cluster"


class ClusterForecastResponse(BaseModel):
    cluster_name: str
    timestamp: str
    aggregated_forecast_MW: float
    confidence_lower: float
    confidence_upper: float
    plant_breakdown: List[dict]
    key_drivers: str


@app.get("/health")
def health():
    return {"status": "ok", "model": "amazon/chronos-bolt-small", "version": "0.1.0"}


def load_inputs():
    scada = pd.read_csv("data/synthetic_scada/synthetic_scada.csv", parse_dates=["timestamp"])
    weather = pd.read_parquet("data/weather/weather_all.parquet")
    scada["timestamp"] = pd.to_datetime(scada["timestamp"]).dt.tz_localize(None)
    weather["timestamp"] = pd.to_datetime(weather["timestamp"]).dt.tz_localize(None)
    return scada, weather


def validate_language(language: str) -> str:
    value = (language or "en").strip().lower()
    if value not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=422, detail=f"Unsupported language '{language}'. Use one of {sorted(SUPPORTED_LANGUAGES)}.")
    return value


def build_forecast_frame(
    pipeline,
    scada: pd.DataFrame,
    weather: pd.DataFrame,
    plant_id: str,
    context_hours: int,
    prediction_hours: int,
    forecast_timestamp: Optional[str] = None,
    language: str = "en",
):
    meta_map = {p["plant_id"]: p for p in PLANTS}
    if plant_id not in meta_map:
        raise HTTPException(status_code=404, detail=f"Unknown plant_id '{plant_id}'.")
    if prediction_hours <= 0 or prediction_hours > 48:
        raise HTTPException(status_code=422, detail="prediction_hours must be between 1 and 48.")
    if context_hours < prediction_hours * 2:
        raise HTTPException(status_code=422, detail="context_hours must be at least 2x prediction_hours.")

    ctx = scada[scada["plant_id"] == plant_id].copy().sort_values("timestamp")
    if ctx.empty:
        raise HTTPException(status_code=404, detail=f"No SCADA data found for '{plant_id}'.")

    if forecast_timestamp:
        ts = pd.to_datetime(forecast_timestamp)
        ctx = ctx[ctx["timestamp"] <= ts]
    else:
        ts = ctx["timestamp"].max()

    ctx = ctx.tail(context_hours)
    if len(ctx) < prediction_hours * 2:
        raise HTTPException(status_code=422, detail=f"Insufficient context for '{plant_id}'. Need at least {prediction_hours * 2} rows.")

    pred_df = forecast_baseline(pipeline, ctx, prediction_length=prediction_hours)
    pred_df["plant_id"] = plant_id

    future_weather = weather[
        (weather["plant_id"] == plant_id) &
        (weather["timestamp"] > ts) &
        (weather["timestamp"] <= ts + pd.Timedelta(hours=prediction_hours))
    ].copy()

    pred_df = apply_residual_layer(pred_df, future_weather, PLANTS)
    pred_df = apply_physics_constraints(pred_df, future_weather, PLANTS)
    pred_df = apply_confidence_bands(pred_df, PLANTS)
    pred_df = generate_explanations(pred_df, language=language)
    pred_df = get_override_manager().apply_overrides(pred_df)

    pred_df["forecast_MW"] = pred_df["final_forecast_MW"].astype(float).round(3)
    pred_df["plant_type"] = meta_map[plant_id]["type"]
    pred_df["requested_language"] = language
    return pred_df


@app.post("/forecast", response_model=List[ForecastResponse])
def forecast(req: ForecastRequest):
    pipeline = get_pipeline()
    scada, weather = load_inputs()
    language = validate_language(req.language)
    pred_df = build_forecast_frame(
        pipeline,
        scada,
        weather,
        req.plant_id,
        req.context_hours,
        req.prediction_hours,
        forecast_timestamp=req.forecast_timestamp,
        language=language,
    )

    results = []
    for _, row in pred_df.iterrows():
        results.append(ForecastResponse(
            plant_id=row["plant_id"],
            timestamp=str(row["timestamp"]),
            forecast_MW=round(float(row["forecast_MW"]), 3),
            confidence_lower=round(float(row["confidence_lower"]), 3),
            confidence_upper=round(float(row["confidence_upper"]), 3),
            explanation=row.get("explanation", ""),
            was_clamped=bool(row.get("was_clamped", False)),
            clamp_reason=row.get("clamp_reason", None),
            drivers={
                "cloud_fraction": round(float(row.get("cloud_fraction", 0)), 3),
                "wind_speed_10m": None if pd.isna(row.get("wind_speed_10m")) else round(float(row.get("wind_speed_10m", 0)), 2),
                "residual_MW": round(float(row.get("residual_MW", 0)), 3),
                "wind_based_MW": None if pd.isna(row.get("wind_based_MW")) else round(float(row.get("wind_based_MW", 0)), 3),
            }
        ))
    return results


@app.post("/forecast/bulk")
def forecast_bulk(file: UploadFile = File(...)):
    """Upload CSV and return batch forecasts as CSV."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
    contents = file.file.read()
    if len(contents) > 2_000_000:
        raise HTTPException(status_code=413, detail="Bulk CSV is too large. Keep uploads under 2 MB.")

    try:
        req_df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}") from exc

    if "plant_id" not in req_df.columns:
        raise HTTPException(status_code=400, detail="CSV must include a plant_id column.")

    pipeline = get_pipeline()
    scada, weather = load_inputs()
    rows = []

    for idx, record in req_df.fillna("").iterrows():
        plant_id = str(record.get("plant_id", "")).strip()
        if not plant_id:
            continue
        prediction_hours = int(record.get("prediction_hours") or 24)
        context_hours = int(record.get("context_hours") or 168)
        raw_forecast_timestamp = record.get("forecast_timestamp")
        if raw_forecast_timestamp in ("", None) or pd.isna(raw_forecast_timestamp):
            forecast_timestamp = None
        else:
            forecast_timestamp = str(raw_forecast_timestamp).strip() or None
        language = validate_language(str(record.get("language") or "en"))

        pred_df = build_forecast_frame(
            pipeline,
            scada,
            weather,
            plant_id,
            context_hours,
            prediction_hours,
            forecast_timestamp=forecast_timestamp,
            language=language,
        )
        pred_df = pred_df.copy()
        pred_df["request_index"] = idx
        pred_df["requested_timestamp"] = forecast_timestamp or ""
        pred_df["requested_prediction_hours"] = prediction_hours
        pred_df["requested_context_hours"] = context_hours
        rows.append(
            pred_df[
                [
                    "request_index",
                    "plant_id",
                    "timestamp",
                    "forecast_MW",
                    "confidence_lower",
                    "confidence_upper",
                    "requested_prediction_hours",
                    "requested_context_hours",
                    "requested_timestamp",
                    "requested_language",
                    "explanation",
                    "was_clamped",
                    "clamp_reason",
                ]
            ]
        )

    if not rows:
        raise HTTPException(status_code=400, detail="No valid rows found in bulk CSV.")

    out_df = pd.concat(rows, ignore_index=True)
    csv_bytes = out_df.to_csv(index=False).encode("utf-8")
    headers = {"Content-Disposition": "attachment; filename=bulk_forecast_results.csv"}
    return StreamingResponse(io.BytesIO(csv_bytes), media_type="text/csv", headers=headers)


@app.post("/forecast/cluster", response_model=List[ClusterForecastResponse])
def forecast_cluster(req: ClusterForecastRequest):
    """
    Aggregate forecasts across multiple plants (cluster/region level).
    Sums individual plant forecasts and combines confidence bands.
    """
    pipeline = get_pipeline()
    scada, weather = load_inputs()
    language = validate_language(req.language)

    all_plant_forecasts = []
    for pid in req.plant_ids:
        pred_df = build_forecast_frame(
            pipeline,
            scada,
            weather,
            pid,
            req.context_hours,
            req.prediction_hours,
            forecast_timestamp=req.forecast_timestamp,
            language=language,
        )
        all_plant_forecasts.append(pred_df)

    if not all_plant_forecasts:
        return []

    combined = pd.concat(all_plant_forecasts, ignore_index=True)
    merged = (
        combined.groupby("timestamp", as_index=False)
        .agg(
            aggregated_forecast_MW=("forecast_MW", "sum"),
            confidence_lower=("confidence_lower", "sum"),
            confidence_upper=("confidence_upper", "sum"),
            physics_events=("was_clamped", "sum"),
        )
        .sort_values("timestamp")
    )

    results = []
    for _, row in merged.iterrows():
        breakdown = []
        for df in all_plant_forecasts:
            sub = df[df["timestamp"] == row["timestamp"]]
            if not sub.empty:
                s = sub.iloc[0]
                breakdown.append({
                    "plant_id": s["plant_id"],
                    "forecast_MW": round(float(s["forecast_MW"]), 1),
                    "explanation": s.get("explanation", "")[:60]
                })
        results.append(ClusterForecastResponse(
            cluster_name=req.cluster_name,
            timestamp=str(row["timestamp"]),
            aggregated_forecast_MW=round(float(row["aggregated_forecast_MW"]), 1),
            confidence_lower=round(float(row["confidence_lower"]), 1),
            confidence_upper=round(float(row["confidence_upper"]), 1),
            plant_breakdown=breakdown,
            key_drivers=f"{len(breakdown)} plants aggregated; {int(row['physics_events'])} physics events"
        ))
    return results


# ── Override Endpoints ──────────────────────────────────────

class OverrideRequest(BaseModel):
    plant_id: str
    start_time: str
    end_time: str
    override_type: str  # zero, cap, scale, absolute
    value: Optional[float] = None
    reason: str
    created_by: str = "operator"


@app.post("/override")
def create_override(req: OverrideRequest):
    """SLDC operator creates an override (maintenance, curtailment, etc.)."""
    mgr = get_override_manager()
    rule = OverrideRule(
        plant_id=req.plant_id,
        start_time=req.start_time,
        end_time=req.end_time,
        override_type=req.override_type,
        value=req.value,
        reason=req.reason,
        created_by=req.created_by,
    )
    mgr.add_rule(rule)
    return {"status": "created", "rule": rule.to_dict()}


@app.get("/overrides")
def list_overrides(plant_id: Optional[str] = None):
    """List active operator overrides."""
    mgr = get_override_manager()
    return {"overrides": mgr.list_rules(plant_id)}


@app.delete("/override/clear")
def clear_expired_overrides():
    """Remove expired override rules."""
    mgr = get_override_manager()
    mgr.clear_expired()
    return {"status": "cleared"}


# ── Data Quality Endpoint ───────────────────────────────────

@app.get("/data-quality")
def data_quality():
    """Run data quality checks on SCADA input and return issues."""
    scada = pd.read_csv("data/synthetic_scada/synthetic_scada.csv", parse_dates=["timestamp"])
    clean, issues = check_data_quality(scada, PLANTS)
    report_path = generate_quality_report(issues)
    return {
        "total_issues": len(issues),
        "critical_count": sum(1 for i in issues if i["severity"] == "critical"),
        "warning_count": sum(1 for i in issues if i["severity"] == "warning"),
        "issues": issues,
        "report_file": report_path,
    }


# ── CERC Compliance Endpoint ────────────────────────────────

@app.get("/compliance")
def compliance():
    """Benchmark forecast accuracy against CERC regulatory limits."""
    forecasts = pd.read_parquet("models/baseline/baseline_forecasts.parquet")
    actuals = pd.read_parquet("models/baseline/baseline_actuals.parquet")
    weather = pd.read_parquet("data/weather/weather_all.parquet")
    for df in (forecasts, actuals, weather):
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)

    postprocessed = []
    for pid in forecasts["plant_id"].unique():
        sub = forecasts[forecasts["plant_id"] == pid].copy()
        future_weather = weather[weather["plant_id"] == pid].copy()
        sub = apply_residual_layer(sub, future_weather, PLANTS)
        sub = apply_physics_constraints(sub, future_weather, PLANTS)
        sub = apply_confidence_bands(sub, PLANTS)
        sub["forecast_MW"] = sub["final_forecast_MW"]
        postprocessed.append(sub[["plant_id", "timestamp", "forecast_MW"]])

    final_forecasts = pd.concat(postprocessed, ignore_index=True)
    metrics = compute_cerc_metrics(final_forecasts, actuals, PLANTS)
    report = generate_cerc_report(metrics)
    return report


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
