import pandas as pd
import requests
import os

# ---------------------------------
# Kerala Cities
# ---------------------------------

cities = {
    "Kottayam": (9.5916, 76.5222),
    "Kochi": (9.9312, 76.2673),
    "Kozhikode": (11.2588, 75.7804),
    "Kannur": (11.8745, 75.3704),
    "Thiruvananthapuram": (8.5241, 76.9366)
}

START_DATE = "2023-01-01"
END_DATE = "2025-08-02"

all_data = []

for city, (lat, lon) in cities.items():

    print(f"Downloading {city}...")

    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}"
        f"&longitude={lon}"
        f"&start_date={START_DATE}"
        f"&end_date={END_DATE}"
        "&daily=temperature_2m_max,temperature_2m_min,"
        "precipitation_sum,wind_speed_10m_max"
        "&timezone=Asia%2FKolkata"
    )

    response = requests.get(url)

    if response.status_code != 200:
        print(f"Failed: {city}")
        continue

    data = response.json()["daily"]

    df = pd.DataFrame(data)

    df["city"] = city

    all_data.append(df)

# ---------------------------------

final_df = pd.concat(all_data, ignore_index=True)

final_df.rename(columns={
    "time":"date",
    "temperature_2m_max":"max_temp",
    "temperature_2m_min":"min_temp",
    "precipitation_sum":"rainfall",
    "wind_speed_10m_max":"max_speed"
}, inplace=True)

os.makedirs("data", exist_ok=True)

final_df.to_csv("data/kerala_weather.csv", index=False)

print("\nDataset Created Successfully!\n")

print(final_df.head())

print("\nTotal Rows :", len(final_df))