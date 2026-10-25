import joblib

from backend.outfit_catalog import (
    OUTFIT_AVATAR_FILES,
    SUPPORTED_LABELS,
    get_ranked_outfits,
)


def test_model_labels_are_supported_by_catalog():
    encoder = joblib.load("model/label_encoder.pkl")
    model_labels = set(encoder.classes_)
    catalog_labels = set(SUPPORTED_LABELS)

    assert model_labels == catalog_labels
    assert len(model_labels) == len(catalog_labels)


def test_catalog_ranking_returns_unique_entries():
    weather = {"max_temp": 31, "min_temp": 24, "rainfall": 0, "max_speed": 12}

    ranked = get_ranked_outfits(weather, style="Casual", occasion="Casual", comfort_level=70)

    assert len(ranked) == len(SUPPORTED_LABELS)
    assert len({item["name"] for item in ranked}) == len(ranked)
    assert all("weather_match_score" in item for item in ranked)
    assert all("clothing_items" in item for item in ranked)
    assert all("accessories" in item for item in ranked)
    assert all("explanation" in item for item in ranked)
    assert ranked[0]["weather_match_score"] >= ranked[-1]["weather_match_score"]


def test_catalog_respects_requested_style_and_occasion_filters():
    weather = {"max_temp": 30, "min_temp": 26, "rainfall": 12, "max_speed": 18}

    ranked = get_ranked_outfits(weather, style="Casual", occasion="Casual", comfort_level=50)
    assert ranked
    assert all(item["style"] in {"Casual", "Any"} or "Casual" in item["style"] for item in ranked)

    formal_ranked = get_ranked_outfits(weather, style="Formal", occasion="Party", comfort_level=60)
    assert formal_ranked
    assert formal_ranked[0]["weather_match_score"] >= 0


def test_catalog_keeps_model_label_as_primary_name():
    weather = {"max_temp": 35, "min_temp": 28, "rainfall": 0, "max_speed": 8}

    ranked = get_ranked_outfits(weather, style="Casual", occasion="Casual", comfort_level=80)
    names = {item["name"] for item in ranked}

    expected_names = {
        "T-Shirt + Shorts + Cap",
        "Cotton T-Shirt + Jeans",
        "Hoodie + Jeans",
        "Windproof Jacket + Jeans",
        "Light Jacket + Umbrella",
        "Rain Jacket + Waterproof Shoes + Umbrella",
    }

    assert names == expected_names


def test_catalog_avatar_map_matches_supported_labels():
    expected = {
        "Rain Jacket + Waterproof Shoes + Umbrella": "avatar_rain_outfit.png",
        "Light Jacket + Umbrella": "avatar_light_jacket.png",
        "T-Shirt + Shorts + Cap": "avatar_summer_outfit.png",
        "Cotton T-Shirt + Jeans": "avatar_cotton_jeans.png",
        "Windproof Jacket + Jeans": "avatar_windproof_jacket.png",
        "Hoodie + Jeans": "avatar_hoodie_jeans.png",
    }

    assert OUTFIT_AVATAR_FILES == expected
    assert set(OUTFIT_AVATAR_FILES) == set(SUPPORTED_LABELS)


def test_catalog_prefers_lightweight_dry_outfit_when_weather_is_warm_and_dry():
    weather = {
        "current": {"weather_code": 0, "precipitation": 0.0},
        "forecast": {"max_temp": 35, "min_temp": 28, "rainfall": 0.0, "max_speed": 8.0},
    }

    ranked = get_ranked_outfits(weather, style="Casual", occasion="Casual", comfort_level=50)

    assert ranked[0]["name"] == "T-Shirt + Shorts + Cap"


def test_catalog_prioritises_rain_protection_when_current_weather_is_rainy_even_if_forecast_total_is_low():
    weather = {
        "current": {"weather_code": 61, "precipitation": 1.2},
        "forecast": {"max_temp": 29, "min_temp": 24, "rainfall": 0.4, "max_speed": 10.0},
    }

    ranked = get_ranked_outfits(weather, style="Casual", occasion="Casual", comfort_level=50)

    assert ranked[0]["name"] in {"Rain Jacket + Waterproof Shoes + Umbrella", "Light Jacket + Umbrella"}


def test_catalog_prefers_windproof_outfit_when_cool_and_windy():
    weather = {
        "current": {"weather_code": 1, "precipitation": 0.0},
        "forecast": {"max_temp": 21, "min_temp": 16, "rainfall": 0.0, "max_speed": 34.0},
    }

    ranked = get_ranked_outfits(weather, style="Casual", occasion="Casual", comfort_level=50)

    assert ranked[0]["name"] == "Windproof Jacket + Jeans"
