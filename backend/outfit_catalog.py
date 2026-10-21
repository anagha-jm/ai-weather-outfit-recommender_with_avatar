"""Outfit catalog and ranking support for Stage 2.

This module is deliberately separate from the trained model so the original
Random Forest artifact and its feature contract remain untouched.
"""

from __future__ import annotations

from typing import Any, Dict, List

SUPPORTED_LABELS = [
    "Rain Jacket + Waterproof Shoes + Umbrella",
    "Light Jacket + Umbrella",
    "T-Shirt + Shorts + Cap",
    "Cotton T-Shirt + Jeans",
    "Windproof Jacket + Jeans",
    "Hoodie + Jeans",
]

OUTFIT_CATALOG: Dict[str, Dict[str, Any]] = {
    "Rain Jacket + Waterproof Shoes + Umbrella": {
        "style": "Casual",
        "occasion": "Any",
        "comfort_target": 35,
        "clothing_items": ["Rain jacket", "Waterproof shoes", "Umbrella"],
        "accessories": ["Weatherproof cap", "Quick-dry socks"],
        "explanation": "A heavy-rain setup keeps you dry and protected when precipitation and wind rise together.",
    },
    "Light Jacket + Umbrella": {
        "style": "Casual",
        "occasion": "Any",
        "comfort_target": 50,
        "clothing_items": ["Light jacket", "Long-sleeve top", "Comfort jeans"],
        "accessories": ["Compact umbrella", "Light scarf"],
        "explanation": "A breathable outer layer is ideal for moderate rain without overheating.",
    },
    "T-Shirt + Shorts + Cap": {
        "style": "Casual",
        "occasion": "Casual",
        "comfort_target": 70,
        "clothing_items": ["Cotton T-shirt", "Shorts"],
        "accessories": ["Cap", "Sunglasses"],
        "explanation": "This combination is best for very hot, dry weather where airflow and light coverage matter most.",
    },
    "Cotton T-Shirt + Jeans": {
        "style": "Casual",
        "occasion": "Casual",
        "comfort_target": 60,
        "clothing_items": ["Cotton T-shirt", "Jeans"],
        "accessories": ["Light belt", "Everyday sneakers"],
        "explanation": "A balanced everyday look suited to warm temperatures with moderate comfort needs.",
    },
    "Windproof Jacket + Jeans": {
        "style": "Casual",
        "occasion": "Any",
        "comfort_target": 45,
        "clothing_items": ["Windproof jacket", "Jeans"],
        "accessories": ["Neck gaiter", "Trail shoes"],
        "explanation": "High wind exposure calls for a protective outer shell while keeping the rest of the outfit practical.",
    },
    "Hoodie + Jeans": {
        "style": "Casual",
        "occasion": "Any",
        "comfort_target": 55,
        "clothing_items": ["Hoodie", "Jeans"],
        "accessories": ["Light beanie", "Casual sneakers"],
        "explanation": "A versatile cool-weather option with gentle warmth and easy layering for mild conditions.",
    },
}


def _prepare_weather(weather: Dict[str, Any]) -> Dict[str, float]:
    forecast = weather or {}
    max_temp = float(forecast.get("max_temp", 25.0))
    min_temp = float(forecast.get("min_temp", max_temp))
    rainfall = float(forecast.get("rainfall", 0.0))
    max_speed = float(forecast.get("max_speed", 0.0))
    return {
        "max_temp": max_temp,
        "min_temp": min_temp,
        "rainfall": rainfall,
        "max_speed": max_speed,
    }


def _style_match(style: str, outfit_style: str) -> int:
    preferred_style = (style or "Casual").strip().lower()
    outfit_style_name = (outfit_style or "Casual").strip().lower()

    if preferred_style == "any":
        return 10
    if outfit_style_name == "any":
        return 12
    if preferred_style == outfit_style_name:
        return 25
    return -10


def _occasion_match(occasion: str, outfit_occasion: str) -> int:
    preferred_occasion = (occasion or "Casual").strip().lower()
    outfit_occasion_name = (outfit_occasion or "Any").strip().lower()

    if preferred_occasion == "any":
        return 8
    if outfit_occasion_name == "any":
        return 12
    if preferred_occasion == outfit_occasion_name:
        return 20
    return -8


def _comfort_match(comfort_level: float, comfort_target: float) -> int:
    comfort = float(comfort_level or 50.0)
    distance = abs(comfort - float(comfort_target))
    return int(max(-20, 15 - distance * 0.35))


def _weather_score(name: str, weather: Dict[str, float]) -> int:
    temperature = weather["max_temp"]
    rainfall = weather["rainfall"]
    wind_speed = weather["max_speed"]

    if name == "Rain Jacket + Waterproof Shoes + Umbrella":
        score = 50 + (35 if rainfall >= 40 else 10 if rainfall >= 10 else -10)
        score += 8 if wind_speed >= 20 else 0
        return max(0, score)

    if name == "Light Jacket + Umbrella":
        score = 48 + (20 if rainfall >= 10 else 8 if rainfall >= 3 else -8)
        score += 6 if temperature <= 30 else 0
        return max(0, score)

    if name == "T-Shirt + Shorts + Cap":
        score = 52 + (22 if temperature >= 35 else 10 if temperature >= 30 else -10)
        score += -10 if rainfall > 0 else 5
        return max(0, score)

    if name == "Cotton T-Shirt + Jeans":
        score = 50 + (18 if temperature >= 30 else 8 if temperature >= 25 else -8)
        score += -8 if rainfall > 15 else 3
        return max(0, score)

    if name == "Windproof Jacket + Jeans":
        score = 46 + (18 if wind_speed >= 25 else 6 if wind_speed >= 15 else -10)
        score += 6 if temperature <= 28 else 0
        return max(0, score)

    if name == "Hoodie + Jeans":
        score = 46 + (18 if temperature >= 25 and temperature <= 30 else 8 if temperature >= 20 else -8)
        score += -4 if rainfall > 20 else 5
        return max(0, score)

    if name == "Sweater + Jacket":
        score = 42 + (18 if temperature < 25 else 8 if temperature < 30 else -8)
        score += 8 if rainfall <= 10 else -8
        return max(0, score)

    return 50


def get_ranked_outfits(
    weather: Dict[str, Any],
    style: str = "Casual",
    occasion: str = "Casual",
    comfort_level: float = 50,
) -> List[Dict[str, Any]]:
    """Return a ranked list of outfit options based on weather and user preferences.

    Each result includes the exact model label name and a detailed outfit object so
    the API can stay backward compatible while exposing richer ranked leads.
    """

    weather_values = _prepare_weather(weather)
    ranked: List[Dict[str, Any]] = []

    for outfit_name in SUPPORTED_LABELS:
        template = OUTFIT_CATALOG[outfit_name]
        base_score = _weather_score(outfit_name, weather_values)
        score = base_score
        score += _style_match(style, template["style"])
        score += _occasion_match(occasion, template["occasion"])
        score += _comfort_match(comfort_level, template["comfort_target"])

        if score < 0:
            score = 0
        if score > 100:
            score = 100

        ranked.append(
            {
                "name": outfit_name,
                "style": template["style"],
                "occasion": template["occasion"],
                "comfort_level": int(template["comfort_target"]),
                "clothing_items": list(template["clothing_items"]),
                "accessories": list(template["accessories"]),
                "explanation": template["explanation"],
                "weather_match_score": int(score),
            }
        )

    ranked.sort(key=lambda item: item["weather_match_score"], reverse=True)
    return ranked
