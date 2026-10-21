from backend.weather_service import get_weather

weather = get_weather("Kottayam")

print("Raw weather response:")
print(weather)
print()

assert weather is not None, "FAIL: Expected weather data, got None"
assert "current" in weather, "FAIL: 'current' key missing from response"
assert "forecast" in weather, "FAIL: 'forecast' key missing from response"

forecast_keys = ["max_temp", "min_temp", "rainfall", "max_speed"]
for k in forecast_keys:
    assert k in weather["forecast"], f"FAIL: '{k}' missing from forecast dict"

assert "weather_description" in weather["current"], (
    "FAIL: 'weather_description' missing — WMO decoder not applied"
)

print("[PASS] All weather service assertions passed.")
print(f"   Current temp : {weather['current']['temperature']} °C")
print(f"   Conditions   : {weather['current']['weather_description']}")
print(f"   Max temp     : {weather['forecast']['max_temp']} °C")
print(f"   Rainfall     : {weather['forecast']['rainfall']} mm")