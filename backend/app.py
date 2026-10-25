import os

from flask import Flask, request, jsonify
from flask_cors import CORS

if __package__:
    from .outfit_catalog import WEATHER_SUITABLE_OUTFITS, get_ranked_outfits
    from .weather_classifier import predict_weather_category
    from .weather_service import get_weather
else:
    from outfit_catalog import WEATHER_SUITABLE_OUTFITS, get_ranked_outfits
    from weather_classifier import predict_weather_category
    from weather_service import get_weather

app = Flask(__name__)

CORS(app)


@app.route("/")
def home():
    return {
        "message": "AI Weather Outfit Recommendation API Running"
    }


@app.route("/predict", methods=["POST"])
def predict():

    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON received"}), 400

    city = data.get("city")

    if not city:
        return jsonify({"error": "City is required"}), 400

    style = data.get("style", "Casual")
    occasion = data.get("occasion", "Casual")
    comfort_level = data.get("comfort_level", 50)

    weather = get_weather(city)

    if weather is None:
        return jsonify({"error": "City not found or weather service unavailable"}), 404

    weather_category = predict_weather_category(weather["forecast"])
    ranked_outfits = get_ranked_outfits(
        weather,
        style=style,
        occasion=occasion,
        comfort_level=comfort_level,
    )
    weather_suitable_outfits = set(WEATHER_SUITABLE_OUTFITS[weather_category])
    ranked_outfits = [
        outfit for outfit in ranked_outfits
        if outfit["name"] in weather_suitable_outfits
    ]
    if not ranked_outfits:
        raise RuntimeError(
            f"No catalog outfits are mapped as suitable for {weather_category!r} weather."
        )
    recommended_outfit = ranked_outfits[0]["name"]

    return jsonify({
        "city": city,
        "current": weather["current"],
        "forecast": weather["forecast"],
        "weather_category": weather_category,
        "recommended_outfit": recommended_outfit,
        "ranked_outfits": ranked_outfits,
        # Echoing received filters so frontend can verify they were received
        "_filters": {
            "style": style,
            "occasion": occasion,
            "comfort_level": comfort_level,
        },
    })


if __name__ == "__main__":
    # Set DEBUG=true in your environment to enable Werkzeug debug mode.
    # Never run with debug=True in production.
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)