"""
Open-Meteo Weather Fetcher for GridSense AI
Pulls hourly weather forecasts and historical data for Karnataka plant coordinates.
Caches results as Parquet to avoid repeated API calls.
"""
import pandas as pd
import os
from pathlib import Path
import sys
import openmeteo_requests
import requests_cache
from retry_requests import retry

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime_config import chdir_project_root, configure_runtime

configure_runtime()
chdir_project_root()

# Plant coordinates (must match scada_generator.py)
PLANT_COORDS = {
    "SOL_PAVAGADA_100": (14.25, 77.28),
    "SOL_KOPPAL_50": (15.35, 76.15),
    "SOL_RAICHUR_200": (16.21, 77.35),
    "WIND_CHITRADURGA_80": (14.23, 76.40),
    "WIND_HASSAN_150": (13.00, 76.10),
}


def setup_client():
    """Setup cached Open-Meteo client."""
    cache_dir = Path(os.environ["XDG_CACHE_HOME"]) / "openmeteo"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_session = requests_cache.CachedSession(str(cache_dir / "http_cache"), expire_after=3600)
    retry_session = retry(cache_session, retries=3, backoff_factor=0.2)
    return openmeteo_requests.Client(session=retry_session)


def fetch_weather_for_plant(plant_id, lat, lon, start_date, end_date, client=None):
    """Fetch hourly weather variables from Open-Meteo."""
    if client is None:
        client = setup_client()

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": [
            "temperature_2m",
            "cloud_cover",
            "shortwave_radiation",  # GHI proxy (W/m2)
            "wind_speed_10m",
            "wind_direction_10m",
            "relative_humidity_2m",
            "surface_pressure",
        ],
        "timezone": "Asia/Kolkata",
    }

    responses = client.weather_api(url, params=params)
    response = responses[0]  # single location

    hourly = response.Hourly()
    times = pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left",
    )
    times = times.tz_convert("Asia/Kolkata")

    df = pd.DataFrame({
        "timestamp": times,
        "plant_id": plant_id,
        "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
        "cloud_cover": hourly.Variables(1).ValuesAsNumpy(),
        "ghi": hourly.Variables(2).ValuesAsNumpy(),
        "wind_speed_10m": hourly.Variables(3).ValuesAsNumpy(),
        "wind_direction_10m": hourly.Variables(4).ValuesAsNumpy(),
        "relative_humidity_2m": hourly.Variables(5).ValuesAsNumpy(),
        "surface_pressure": hourly.Variables(6).ValuesAsNumpy(),
    })
    return df


def fetch_all_weather(start_date="2025-01-01", end_date="2025-03-31", output_dir="data/weather"):
    """Fetch weather for all plants and save as Parquet."""
    client = setup_client()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    all_dfs = []
    for plant_id, (lat, lon) in PLANT_COORDS.items():
        print(f"Fetching weather for {plant_id} ...")
        df = fetch_weather_for_plant(plant_id, lat, lon, start_date, end_date, client)
        all_dfs.append(df)

    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all = df_all.sort_values(["plant_id", "timestamp"]).reset_index(drop=True)

    out_file = output_path / "weather_all.parquet"
    df_all.to_parquet(out_file, index=False)
    print(f"Saved weather data to {out_file} ({len(df_all)} rows)")
    return df_all


if __name__ == "__main__":
    fetch_all_weather()
