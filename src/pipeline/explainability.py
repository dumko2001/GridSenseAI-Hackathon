"""
Explainability Engine — 100% Offline
Generates human-readable forecast explanations using deterministic templates.
No LLMs. No external APIs. Fully air-gappable.

Why templates over LLMs for this use case:
1. Deterministic: same input → same explanation (auditable, testable)
2. Faster: zero API latency (~0ms vs ~500ms for LLM call)
3. Cheaper: zero cost per explanation
4. More operationally useful: includes exact MW values, physics reasons, and clamp details
5. Fully compliant: no hosted LLM usage whatsoever

A grid operator cares about: "Why is Pavagada forecast 64 MW at noon?"
Template answer: "Solar plant at 12:00 IST: Baseline forecast 82 MW. Downward adjustment of 18 MW due to cloud cover (37%). Output capped by clear-sky GHI limit."
LLM answer: "At 12:00 IST, expect moderate solar generation under partly cloudy skies."

The template is objectively more useful for operational decision-making.
"""
import pandas as pd


SUPPORTED_LANGUAGES = {"en", "kn"}


def _normalize_language(language: str | None) -> str:
    value = (language or "en").strip().lower()
    return value if value in SUPPORTED_LANGUAGES else "en"


def generate_explanation(row):
    """Generate operationally useful explanation from forecast row."""
    language = _normalize_language(row.get("language"))
    parts = []
    plant_type = "Solar" if "SOL_" in str(row.get("plant_id", "")) else "Wind"
    base = row.get("predictions", row.get("baseline_MW", 0))
    res = row.get("residual_MW", 0)
    final = row.get("final_forecast_MW", 0)
    clamp = row.get("clamp_reason", "")
    cloud = row.get("cloud_fraction", 0)
    ws = row.get("wind_speed_10m", 0)
    hour = pd.to_datetime(row["timestamp"]).hour
    is_wind = plant_type == "Wind"

    if language == "kn":
        parts.append(f"{'ಸೌರ' if not is_wind else 'ಗಾಳಿ'} ಘಟಕ {hour:02d}:00 IST:")
        parts.append(f"ಮೂಲ ಅಂದಾಜು {base:.1f} MW.")
        if abs(res) > 1:
            if is_wind and pd.notna(ws):
                parts.append(f"ಗಾಳಿ ವೇಗ {float(ws):.1f} m/s ಆಧಾರವಾಗಿ {final:.1f} MW ಗೆ ಸರಿಪಡಿಸಲಾಗಿದೆ.")
            elif res < 0:
                parts.append(f"ಮೋಡಾವರಣ ({cloud*100:.0f}%) ಕಾರಣ {abs(res):.1f} MW ಇಳಿಕೆ.")
            else:
                parts.append(f"{res:.1f} MW ಹೆಚ್ಚುವರಿ ಸರಿಪಡింపు.")
        if clamp:
            parts.append(f"ಭೌತಿಕ ಮಿತಿ ಅನ್ವಯಿಸಲಾಗಿದೆ: {clamp}")
        if final < base * 0.8:
            parts.append("ಹವಾಮಾನ ಅಸ್ಥಿರತೆಯಿಂದ ವಿಶ್ವಾಸ ವ್ಯಾಪ್ತಿ ವಿಸ್ತರಿಸಲಾಗಿದೆ.")
        return " ".join(parts)

    parts.append(f"{plant_type} plant at {hour:02d}:00 IST:")
    parts.append(f"Baseline forecast {base:.1f} MW.")

    if abs(res) > 1:
        if is_wind and pd.notna(ws):
            parts.append(
                f"Weather-driven adjustment to {final:.1f} MW based on {float(ws):.1f} m/s wind speed."
            )
        elif res < 0:
            parts.append(f"Downward adjustment of {abs(res):.1f} MW due to cloud cover ({cloud*100:.0f}%).")
        else:
            parts.append(f"Upward adjustment of {res:.1f} MW.")

    if clamp:
        parts.append(f"Output capped: {clamp}")

    if final < base * 0.8:
        parts.append("Confidence band widened due to high weather volatility.")

    return " ".join(parts)


def generate_explanations(df, language: str | None = None):
    """Add explanation column to forecast DataFrame."""
    df = df.copy()
    if language is not None:
        df["language"] = _normalize_language(language)
    elif "language" in df.columns:
        df["language"] = df["language"].map(_normalize_language)
    else:
        df["language"] = "en"
    df["explanation"] = df.apply(generate_explanation, axis=1)
    return df


if __name__ == "__main__":
    from data.scada_generator import PLANTS
    from pipeline.residual_adjuster import apply_residual_layer
    from pipeline.physics_constraints import apply_physics_constraints
    bf = pd.read_parquet("models/baseline/baseline_forecasts.parquet")
    wf = pd.read_parquet("data/weather/weather_all.parquet")
    res = apply_residual_layer(bf, wf, PLANTS)
    phy = apply_physics_constraints(res, wf, PLANTS)
    out = generate_explanations(phy)
    print(out[["plant_id", "timestamp", "final_forecast_MW", "explanation"]].head(5))
