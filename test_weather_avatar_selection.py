import re

import pytest

from backend import app as backend_app
from backend.outfit_catalog import OUTFIT_AVATAR_FILES, WEATHER_SUITABLE_OUTFITS
from backend.weather_classifier import (
    load_weather_classifier,
    predict_weather_category,
)
from frontend import app as frontend_app


OCCASIONS = [
    "Casual",
    "College",
    "Work / Formal",
    "Presentation",
    "Interview",
    "Outdoor / Sports",
    "Party",
]
VIBES = ["Light & Breezy", "Balanced Comfort", "Warm & Cozy"]
GENDERS = ["male", "female"]
WEATHER_CATEGORIES = ["hot", "cold", "rainy"]


@pytest.mark.parametrize("gender", GENDERS)
@pytest.mark.parametrize("occasion", OCCASIONS)
@pytest.mark.parametrize("vibe", VIBES)
@pytest.mark.parametrize("weather_category", WEATHER_CATEGORIES)
def test_all_preference_combinations_return_existing_weather_safe_images(
    gender, occasion, vibe, weather_category
):
    selection = frontend_app.select_weather_avatar(
        gender, weather_category, occasion, vibe
    )

    assert selection.image_path is not None
    assert selection.image_path.is_file()
    assert selection.image_path.parent.name == gender
    stem = re.sub(r"\s*\(\d+\)$", "", selection.image_path.stem).casefold()

    if weather_category == "rainy":
        assert stem == "avatar_rain_outfit"
    elif weather_category == "hot":
        preferred_stem = (
            f"{frontend_app.OCCASION_IMAGE_KEYS[occasion]}_light"
        )
        if stem != preferred_stem:
            assert selection.image_path.name in {
                OUTFIT_AVATAR_FILES[name]
                for name in WEATHER_SUITABLE_OUTFITS["hot"]
            }
    else:
        preferred_stem = (
            f"{frontend_app.OCCASION_IMAGE_KEYS[occasion]}_warm"
        )
        if stem != preferred_stem:
            assert selection.image_path.name in {
                OUTFIT_AVATAR_FILES[name]
                for name in WEATHER_SUITABLE_OUTFITS["cold"]
            }


def test_weather_compatible_vibe_overrides_user_vibe():
    hot_selection = frontend_app.select_weather_avatar(
        "female", "hot", "Party", "Warm & Cozy"
    )
    cold_selection = frontend_app.select_weather_avatar(
        "male", "cold", "Work / Formal", "Light & Breezy"
    )

    assert hot_selection.image_path.stem.startswith("party_light")
    assert "light" in hot_selection.fallback_message
    assert cold_selection.image_path.stem.startswith("work_warm")
    assert "warm" in cold_selection.fallback_message


def test_missing_gender_occasion_image_uses_same_gender_weather_safe_fallback():
    selection = frontend_app.select_weather_avatar(
        "male", "hot", "Presentation", "Light & Breezy"
    )

    assert selection.image_path.name == "avatar_summer_outfit.png"
    assert selection.image_path.parent.name == "male"
    assert "No Presentation image" in selection.fallback_message


def test_rainy_selection_uses_explicit_rain_outfit_fallback():
    selection = frontend_app.select_weather_avatar(
        "female", "rainy", "College", "Light & Breezy"
    )

    assert selection.image_path.name == "avatar_rain_outfit.png"
    assert selection.image_path.parent.name == "female"
    assert "no occasion/vibe image" in selection.fallback_message.casefold()


def test_filename_matching_ignores_case_separators_extensions_and_copy_suffix(
    tmp_path, monkeypatch
):
    gender_dir = tmp_path / "male"
    gender_dir.mkdir()
    preferred_image = gender_dir / "WoRK-LiGhT.JPEG"
    preferred_image.touch()
    (gender_dir / "work_light (1).PNG").touch()
    (gender_dir / "network_light.webp").touch()
    monkeypatch.setattr(frontend_app, "AVATAR_BASE_DIR", tmp_path)

    selection = frontend_app.select_weather_avatar(
        "MALE", "hot", "Work / Formal", "Light & Breezy"
    )

    assert selection.image_path == preferred_image


def test_selection_never_searches_another_gender_folder(tmp_path, monkeypatch):
    (tmp_path / "male").mkdir()
    female_dir = tmp_path / "female"
    female_dir.mkdir()
    (female_dir / "avatar_summer_outfit.png").touch()
    monkeypatch.setattr(frontend_app, "AVATAR_BASE_DIR", tmp_path)

    selection = frontend_app.select_weather_avatar(
        "male", "hot", "Presentation", "Light & Breezy"
    )

    assert selection.image_path is None
    assert "male" in selection.fallback_message


def test_selection_never_falls_back_to_another_weather_category(
    tmp_path, monkeypatch
):
    male_dir = tmp_path / "male"
    male_dir.mkdir()
    (male_dir / "avatar_summer_outfit.png").touch()
    monkeypatch.setattr(frontend_app, "AVATAR_BASE_DIR", tmp_path)

    selection = frontend_app.select_weather_avatar(
        "male", "cold", "Presentation", "Warm & Cozy"
    )

    assert selection.image_path is None
    assert "cold-suitable" in selection.fallback_message


@pytest.mark.parametrize(
    ("forecast", "expected"),
    [
        (
            {"min_temp": 29, "max_temp": 38, "rainfall": 0, "max_speed": 12},
            "hot",
        ),
        (
            {"min_temp": 9, "max_temp": 17, "rainfall": 0, "max_speed": 10},
            "cold",
        ),
        (
            {"min_temp": 22, "max_temp": 28, "rainfall": 50, "max_speed": 14},
            "rainy",
        ),
    ],
)
def test_trained_classifier_predicts_weather_category(forecast, expected):
    assert predict_weather_category(forecast) == expected


@pytest.mark.parametrize("weather_category", WEATHER_CATEGORIES)
def test_flask_prediction_uses_classifier_category_to_filter_outfits(
    monkeypatch, weather_category
):
    weather = {
        "current": {"temperature": 24, "humidity": 60, "wind_speed": 10},
        "forecast": {
            "min_temp": 20,
            "max_temp": 28,
            "rainfall": 0,
            "max_speed": 10,
        },
    }

    def fake_get_weather(city):
        assert city == "Test City"
        return weather

    def fake_predict_weather_category(forecast):
        assert forecast == weather["forecast"]
        return weather_category

    monkeypatch.setattr(backend_app, "get_weather", fake_get_weather)
    monkeypatch.setattr(
        backend_app,
        "predict_weather_category",
        fake_predict_weather_category,
    )

    response = backend_app.app.test_client().post(
        "/predict",
        json={
            "city": "Test City",
            "style": "Casual",
            "occasion": "Casual",
            "comfort_level": 50,
        },
    )

    assert response.status_code == 200
    result = response.get_json()
    assert result["weather_category"] == weather_category
    allowed_outfits = set(WEATHER_SUITABLE_OUTFITS[weather_category])
    assert result["recommended_outfit"] in allowed_outfits
    assert {item["name"] for item in result["ranked_outfits"]} <= allowed_outfits


def test_classifier_rejects_missing_features():
    with pytest.raises(ValueError, match="missing features"):
        predict_weather_category({"min_temp": 10})


def test_missing_weather_model_raises_actionable_error(tmp_path):
    with pytest.raises(RuntimeError, match="Weather classifier not found"):
        load_weather_classifier(tmp_path / "missing_weather_classifier.pkl")


def test_frontend_rejects_unsupported_weather_category(monkeypatch):
    response_data = {
        "city": "Test City",
        "current": {},
        "forecast": {},
        "weather_category": "snowy",
    }

    class MockResponse:
        status_code = 200

        def json(self):
            return response_data

    def fake_post(url, **kwargs):
        assert url.endswith("/predict")
        assert "json" in kwargs
        return MockResponse()

    monkeypatch.setattr(frontend_app.requests, "post", fake_post)

    with pytest.raises(ValueError, match="invalid weather category"):
        frontend_app.fetch_recommendation("Test City", "Casual", "Casual", 50)
