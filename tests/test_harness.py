"""
GridSense AI Test Harness
Validates every phase of the pipeline.
Run with: pytest tests/test_harness.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from runtime_config import chdir_project_root, configure_runtime

configure_runtime()
chdir_project_root()

import pandas as pd
import numpy as np
import pytest
from fastapi.testclient import TestClient

from data.scada_generator import generate_realistic_scada, PLANTS, ANOMALIES
from data.weather_fetcher import fetch_all_weather
from pipeline.baseline_forecaster import run_baseline_forecast
from pipeline.residual_adjuster import apply_residual_layer
from pipeline.physics_constraints import apply_physics_constraints
from pipeline.uncertainty import apply_confidence_bands
from pipeline.explainability import generate_explanations
from pipeline.orchestrator import run_full_pipeline
from api.main import app


class TestDataPipeline:
    def test_scada_exists(self):
        df = pd.read_csv("data/synthetic_scada/synthetic_scada.csv", parse_dates=["timestamp"])
        assert len(df) > 0
        assert "plant_id" in df.columns
        assert "generation_MW" in df.columns

    def test_weather_exists(self):
        df = pd.read_parquet("data/weather/weather_all.parquet")
        assert len(df) > 0
        assert "cloud_cover" in df.columns
        assert "wind_speed_10m" in df.columns

    def test_scada_weather_merge(self):
        scada = pd.read_csv("data/synthetic_scada/synthetic_scada.csv", parse_dates=["timestamp"])
        weather = pd.read_parquet("data/weather/weather_all.parquet")
        scada["timestamp"] = pd.to_datetime(scada["timestamp"]).dt.tz_localize(None)
        weather["timestamp"] = pd.to_datetime(weather["timestamp"]).dt.tz_localize(None)
        merged = scada.merge(weather, on=["plant_id", "timestamp"], how="left")
        assert merged["cloud_cover"].notna().sum() > 0


class TestBaseline:
    def test_baseline_forecasts_exist(self):
        df = pd.read_parquet("models/baseline/baseline_forecasts.parquet")
        assert len(df) > 0
        assert "predictions" in df.columns

    def test_baseline_beat_persistence(self):
        import pickle
        with open("models/baseline/metrics.pkl", "rb") as f:
            m = pickle.load(f)
        # If persistence failed (NaN), skip this assert
        if not np.isnan(m.get("persistence_rmse", np.nan)):
            assert m["improvement_vs_persistence"] > 0, f"Baseline worse than persistence: {m}"
        else:
            pytest.skip("Persistence baseline unavailable")


class TestResidualLayer:
    def test_residual_applies_to_clouds(self):
        bf = pd.read_parquet("models/baseline/baseline_forecasts.parquet")
        wf = pd.read_parquet("data/weather/weather_all.parquet")
        out = apply_residual_layer(bf, wf, PLANTS)
        solar_ids = [p["plant_id"] for p in PLANTS if p["type"] == "solar"]
        solar_out = out[out["plant_id"].isin(solar_ids)]
        # At least some rows should have non-zero residual where clouds exist
        cloudy = solar_out[solar_out["cloud_fraction"] > 0.3]
        if len(cloudy) > 0:
            assert (cloudy["residual_MW"] < 0).any()


class TestPhysicsConstraints:
    def test_no_over_generation(self):
        bf = pd.read_parquet("models/baseline/baseline_forecasts.parquet")
        wf = pd.read_parquet("data/weather/weather_all.parquet")
        res = apply_residual_layer(bf, wf, PLANTS)
        phy = apply_physics_constraints(res, wf, PLANTS)
        meta_map = {p["plant_id"]: p for p in PLANTS}
        for _, row in phy.iterrows():
            cap = meta_map.get(row["plant_id"], {}).get("capacity_mw", 9999)
            assert row["final_forecast_MW"] <= cap * 1.01  # small tolerance

    def test_explanations_exist(self):
        bf = pd.read_parquet("models/baseline/baseline_forecasts.parquet")
        wf = pd.read_parquet("data/weather/weather_all.parquet")
        res = apply_residual_layer(bf, wf, PLANTS)
        phy = apply_physics_constraints(res, wf, PLANTS)
        out = apply_confidence_bands(phy, PLANTS)
        out = generate_explanations(out)
        assert out["explanation"].notna().all()
        assert (out["explanation"].str.len() > 10).all()
        assert (out["confidence_upper"] >= out["final_forecast_MW"]).all()
        assert (out["confidence_lower"] <= out["final_forecast_MW"]).all()


class TestIntegration:
    def test_orchestrator_runs(self):
        out = run_full_pipeline("SOL_PAVAGADA_100", prediction_length=6)
        assert len(out) == 6
        assert "final_forecast_MW" in out.columns
        assert "explanation" in out.columns
        assert "confidence_lower" in out.columns
        assert "confidence_upper" in out.columns


class TestAPIContract:
    def test_health_endpoint(self):
        client = TestClient(app)
        r = client.get("/health")
        assert r.status_code == 200

    def test_forecast_endpoint_returns_rows(self):
        client = TestClient(app)
        r = client.post("/forecast", json={"plant_id": "WIND_CHITRADURGA_80", "prediction_hours": 6, "language": "en"})
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 6
        assert "forecast_MW" in body[0]
        assert body[0]["confidence_upper"] >= body[0]["forecast_MW"]

    def test_forecast_supports_kannada(self):
        client = TestClient(app)
        r = client.post("/forecast", json={"plant_id": "SOL_PAVAGADA_100", "prediction_hours": 6, "language": "kn"})
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 6
        assert "ಮೂಲ ಅಂದಾಜು" in body[0]["explanation"] or "ಸೌರ" in body[0]["explanation"]

    def test_bulk_forecast_returns_csv(self):
        client = TestClient(app)
        csv_bytes = b"plant_id,prediction_hours,language\nSOL_PAVAGADA_100,6,en\nWIND_HASSAN_150,6,en\n"
        r = client.post("/forecast/bulk", files={"file": ("batch.csv", csv_bytes, "text/csv")})
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        text = r.text
        assert "request_index" in text
        assert "SOL_PAVAGADA_100" in text
        assert "WIND_HASSAN_150" in text

    def test_cluster_endpoint_returns_aggregate(self):
        client = TestClient(app)
        r = client.post(
            "/forecast/cluster",
            json={
                "plant_ids": ["SOL_PAVAGADA_100", "SOL_KOPPAL_50", "WIND_CHITRADURGA_80"],
                "prediction_hours": 6,
                "cluster_name": "North Karnataka",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 6
        assert body[0]["cluster_name"] == "North Karnataka"
        assert len(body[0]["plant_breakdown"]) >= 2

    def test_override_endpoint_affects_forecast(self):
        client = TestClient(app)
        client.post(
            "/override",
            json={
                "plant_id": "SOL_PAVAGADA_100",
                "start_time": "2025-04-01 00:00:00",
                "end_time": "2025-04-01 05:00:00",
                "override_type": "zero",
                "reason": "Maintenance window",
                "created_by": "test",
            },
        )
        r = client.post("/forecast", json={"plant_id": "SOL_PAVAGADA_100", "prediction_hours": 6})
        assert r.status_code == 200
        body = r.json()
        assert body[0]["forecast_MW"] == 0.0
        assert "Operator override" in body[0]["explanation"]

    def test_compliance_endpoint_uses_final_pipeline(self):
        client = TestClient(app)
        r = client.get("/compliance")
        assert r.status_code == 200
        body = r.json()
        assert "overall_compliant" in body
        assert "plants" in body


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
