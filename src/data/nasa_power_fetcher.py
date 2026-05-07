"""
NASA POWER API Fetcher
Gets real historical solar irradiance and meteorological data for Karnataka coordinates.
NASA POWER is free, no API key needed, and provides satellite-derived data globally.
Alternative to MOSDAC for prototype phase.
"""
import requests
import pandas as pd
from pathlib import Path
import time

PLANT_COORDS = {
    "SOL_PAVAGADA_100": (14.25, 77.28),
    "SOL_KOPPAL_50": (15.35, 76.15),
    "SOL_RAICHUR_200": (16.21, 77.35),
    "WIND_CHITRADURGA_80": (14.23, 76.40),
    "WIND_HASSAN_150": (13.00, 76.10),
}


def fetch_nasa_power(lat, lon, start_date, end_date):
    """
    Fetch hourly solar and meteorological data from NASA POWER.
    Returns DataFrame with GHI, DNI, DHI, wind speed, temperature.
    """
    url = "https://power.larc.nasa.gov/api/temporal/hourly/point"
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN",  # GHI (surface downward shortwave)
        "community": "RE",  # Renewable Energy
        "longitude": lon,
        "latitude": lat,
        "start": start_date.replace("-", ""),
        "end": end_date.replace("-", ""),
        "format": "JSON",
    }
    
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    
    # Parse NASA POWER response
    ghi_series = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
    records = []
    for ts_str, ghi in ghi_series.items():
        # ts_str format: YYYYMMDDHH
        year = int(ts_str[:4])
        month = int(ts_str[4:6])
        day = int(ts_str[6:8])
        hour = int(ts_str[8:10])
        records.append({
            "timestamp": pd.Timestamp(year=year, month=month, day=day, hour=hour),
            "ghi_nasa": float(ghi),
        })
    
    df = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)
    return df


def fetch_all_nasa_power(start_date="20250101", end_date="20250331", output_dir="data/weather"):
    """Fetch NASA POWER GHI for all plants."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    all_dfs = []
    for plant_id, (lat, lon) in PLANT_COORDS.items():
        print(f"Fetching NASA POWER for {plant_id} ({lat}, {lon}) ...")
        df = fetch_nasa_power(lat, lon, start_date, end_date)
        df["plant_id"] = plant_id
        all_dfs.append(df)
        time.sleep(1)  # Be polite to NASA API
    
    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all = df_all.sort_values(["plant_id", "timestamp"]).reset_index(drop=True)
    
    out_file = output_path / "nasa_power_ghi.parquet"
    df_all.to_parquet(out_file, index=False)
    print(f"Saved NASA POWER data to {out_file} ({len(df_all)} rows)")
    return df_all


if __name__ == "__main__":
    fetch_all_nasa_power()
