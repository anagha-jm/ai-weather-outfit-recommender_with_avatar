from pathlib import Path

import pandas as pd
import requests

BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = BASE_DIR / "data" / "kerala_weather.csv"

# WMO Weather Interpretation Codes → human-readable descriptions
# Reference: https://open-meteo.com/en/docs (WMO code table)
WMO_DESCRIPTIONS = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Icy Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    56: "Light Freezing Drizzle",
    57: "Heavy Freezing Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    66: "Light Freezing Rain",
    67: "Heavy Freezing Rain",
    71: "Slight Snowfall",
    73: "Moderate Snowfall",
    75: "Heavy Snowfall",
    77: "Snow Grains",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    85: "Slight Snow Showers",
    86: "Heavy Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Slight Hail",
    99: "Thunderstorm with Heavy Hail",
}


def get_coordinates(city):
    url = (
        f"https://geocoding-api.open-meteo.com/v1/search"
        f"?name={city}&count=1&language=en&format=json"
    )

    try:
        response = requests.get(url, timeout=10)
    except requests.exceptions.Timeout:
        return None
    except requests.exceptions.RequestException:
        return None

    if response.status_code != 200:
        return None

    data = response.json()

    # Guard: key missing OR list is empty
    if not data.get("results"):
        return None

    result = data["results"][0]

    return result["latitude"], result["longitude"]


def _get_local_weather(city):
    if not DATASET_PATH.exists():
        return None

    try:
        df = pd.read_csv(DATASET_PATH)
    except Exception:
        return None

    if df.empty:
        return None

    normalized_city = str(city).strip().lower()
    matches = df[df["city"].str.lower() == normalized_city]
    if matches.empty:
        return None

    row = matches.iloc[0]
    rainfall = float(row["rainfall"])
    weather_code = 63 if rainfall > 0 else 1
    humidity = 80 if rainfall > 10 else 65 if rainfall > 0 else 52

    return {
        "current": {
            "temperature": float(row["max_temp"]),
            "humidity": int(humidity),
            "wind_speed": float(row["max_speed"]),
            "weather_code": weather_code,
            "weather_description": WMO_DESCRIPTIONS.get(weather_code, "Unknown"),
        },
        "forecast": {
            "max_temp": float(row["max_temp"]),
            "min_temp": float(row["min_temp"]),
            "rainfall": rainfall,
            "max_speed": float(row["max_speed"]),
        },
    }


def get_weather(city):

    coordinates = get_coordinates(city)

    if coordinates is not None:
        latitude, longitude = coordinates

        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={latitude}"
            f"&longitude={longitude}"
            "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,precipitation"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
            "&timezone=auto"
            "&forecast_days=1"
        )

        try:
            response = requests.get(url, timeout=10)
        except requests.exceptions.Timeout:
            return _get_local_weather(city)
        except requests.exceptions.RequestException:
            return _get_local_weather(city)

        if response.status_code == 200:
            data = response.json()

            current = data["current"]
            daily = data["daily"]

            weather_code = current["weather_code"]

            return {
                "current": {
                    "temperature": current["temperature_2m"],
                    "humidity": current["relative_humidity_2m"],
                    "wind_speed": current["wind_speed_10m"],
                    "weather_code": weather_code,
                    "weather_description": WMO_DESCRIPTIONS.get(weather_code, "Unknown"),
                    "precipitation": current.get("precipitation", 0.0),
                },
                "forecast": {
                    "max_temp": daily["temperature_2m_max"][0],
                    "min_temp": daily["temperature_2m_min"][0],
                    "rainfall": daily["precipitation_sum"][0],
                    "max_speed": daily["wind_speed_10m_max"][0],
                },
            }

    return _get_local_weather(city)