import joblib

from backend.outfit_catalog import (
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
