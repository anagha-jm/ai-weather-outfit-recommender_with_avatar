import os

from flask import Flask, request, jsonify
from flask_cors import CORS

from weather_service import get_weather
from predictor import predict_outfit
from outfit_catalog import get_ranked_outfits

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

    # Accept style, occasion, comfort_level from frontend.
    # Currently logged for visibility; will be wired to outfit catalog in Stage 2.
    style = data.get("style", "Casual")
    occasion = data.get("occasion", "Casual")
    comfort_level = data.get("comfort_level", 50)

    weather = get_weather(city)

    if weather is None:
        return jsonify({"error": "City not found or weather service unavailable"}), 404

    outfit = predict_outfit(weather["forecast"])
    ranked_outfits = get_ranked_outfits(
        weather["forecast"],
        style=style,
        occasion=occasion,
        comfort_level=comfort_level,
    )

    return jsonify({
        "city": city,
        "current": weather["current"],
        "forecast": weather["forecast"],
        "recommended_outfit": outfit,
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