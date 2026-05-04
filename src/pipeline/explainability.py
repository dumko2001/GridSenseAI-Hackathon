"""
Explainability Engine
Generates human-readable forecast explanations.
Uses Groq API (Llama 3.1 70B) for fast, cheap natural language generation on NON-SENSITIVE weather metadata only.
Falls back to template-based explanations if API is unavailable.

SECURITY NOTE: We NEVER send SCADA generation values, plant IDs, or any sensitive grid data to Groq.
Only weather parameters (cloud %, wind speed, GHI, temperature) and generic plant type (solar/wind) are sent.
"""
import os
import pandas as pd
from dotenv import load_dotenv

try:
    from groq import Groq
except ImportError:
    Groq = None

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"  # Fast, cheap, high quality


def get_groq_client():
    if Groq is None or not GROQ_API_KEY:
        return None
    return Groq(api_key=GROQ_API_KEY)


def template_explanation(row):
    """Fallback template explanation when API is unavailable."""
    parts = []
    plant_type = "Solar" if "SOL_" in str(row.get("plant_id", "")) else "Wind"
    base = row.get("predictions", row.get("baseline_MW", 0))
    res = row.get("residual_MW", 0)
    final = row.get("final_forecast_MW", 0)
    clamp = row.get("clamp_reason", "")
    cloud = row.get("cloud_fraction", 0)
    ws = row.get("wind_speed_10m", 0)
    hour = pd.to_datetime(row["timestamp"]).hour

    parts.append(f"{plant_type} plant at {hour:02d}:00 IST:")
    parts.append(f"Baseline forecast {base:.1f} MW.")

    if abs(res) > 1:
        if res < 0:
            parts.append(f"Downward adjustment of {abs(res):.1f} MW due to cloud cover ({cloud*100:.0f}%).")
        else:
            parts.append(f"Upward adjustment of {res:.1f} MW.")

    if clamp:
        parts.append(f"Output capped: {clamp}")

    if final < base * 0.8:
        parts.append("Confidence band widened due to high weather volatility.")

    return " ".join(parts)


def build_safe_prompt(row):
    """
    Build a prompt using ONLY non-sensitive weather metadata.
    No plant IDs, no exact SCADA values, no grid-specific identifiers.
    """
    plant_type = "Solar" if "SOL_" in str(row.get("plant_id", "")) else "Wind"
    base = row.get("predictions", row.get("baseline_MW", 0))
    res = row.get("residual_MW", 0)
    final = row.get("final_forecast_MW", 0)
    clamp = row.get("clamp_reason", "")
    cloud = row.get("cloud_fraction", 0)
    ws = row.get("wind_speed_10m", 0)
    ghi = row.get("ghi", 0)
    hour = pd.to_datetime(row["timestamp"]).hour

    # Round values to avoid precision leakage; handle NaN
    base_r = round(base, 1) if pd.notna(base) else 0.0
    res_r = round(res, 1) if pd.notna(res) else 0.0
    final_r = round(final, 1) if pd.notna(final) else 0.0
    ws_r = round(ws, 1) if pd.notna(ws) else 0.0
    ghi_r = int(round(ghi)) if pd.notna(ghi) else 0
    cloud_r = int(round(cloud * 100)) if pd.notna(cloud) else 0

    return (
        f"You are a grid operations assistant. Explain this {plant_type.lower()} generation forecast in one concise sentence for a power grid operator. "
        f"Time: {hour:02d}:00 IST. "
        f"Baseline forecast: {base_r} MW. "
        f"Weather adjustment: {res_r} MW. "
        f"Final forecast: {final_r} MW. "
        f"Cloud cover: {cloud_r}%. "
        f"Wind speed: {ws_r} m/s. "
        f"GHI: {ghi_r} W/m2. "
        f"Constraint: {clamp or 'None'}."
    )


def groq_explanation(prompt_text):
    """Call Groq API for natural language explanation. Returns text or None."""
    client = get_groq_client()
    if not client:
        return None
    try:
        chat = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a grid operations assistant. Be concise, factual, and operationally relevant. One sentence only."},
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.3,
            max_tokens=80,
            timeout=10,
        )
        return chat.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq API error: {e}")
        return None


def generate_explanations(df, use_api=True):
    """Add explanation column to forecast DataFrame."""
    df = df.copy()
    explanations = []
    for _, row in df.iterrows():
        expl = None
        if use_api and GROQ_API_KEY:
            prompt = build_safe_prompt(row)
            expl = groq_explanation(prompt)
        if not expl:
            expl = template_explanation(row)
        explanations.append(expl)
    df["explanation"] = explanations
    return df


if __name__ == "__main__":
    from data.scada_generator import PLANTS
    from pipeline.residual_adjuster import apply_residual_layer
    from pipeline.physics_constraints import apply_physics_constraints
    bf = pd.read_parquet("models/baseline/baseline_forecasts.parquet")
    wf = pd.read_parquet("data/weather/weather_all.parquet")
    res = apply_residual_layer(bf, wf, PLANTS)
    phy = apply_physics_constraints(res, wf, PLANTS)
    out = generate_explanations(phy, use_api=True)
    print(out[["plant_id", "timestamp", "final_forecast_MW", "explanation"]].head(5))
