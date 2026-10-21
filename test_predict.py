from backend.weather_service import get_weather
from backend.predictor import predict_outfit

city = "Kottayam"

weather = get_weather(city)

print("Raw weather response:")
print(weather)
print()

if weather is None:
    print("ERROR: weather service returned None — check city name or network.")
else:
    print("Forecast dict:", weather["forecast"])
    print()
    print("Recommended Outfit:", predict_outfit(weather["forecast"]))