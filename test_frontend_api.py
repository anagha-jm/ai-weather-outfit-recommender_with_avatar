import pytest

from backend.outfit_catalog import OUTFIT_AVATAR_FILES
from frontend import app as frontend_app


class MockResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

    def json(self):
        return self.data


def weather_response(**extra):
    return {
        "city": "Kottayam",
        "current": {
            "humidity": 98,
            "temperature": 24.3,
            "weather_code": 3,
            "wind_speed": 11.1,
        },
        "forecast": {
            "max_speed": 14.4,
            "max_temp": 27.9,
            "min_temp": 23.3,
            "rainfall": 32.7,
        },
        **extra,
    }


def test_fetch_recommendation_accepts_legacy_single_outfit_without_faking_a_ranking(monkeypatch):
    response_data = weather_response(recommended_outfit="Light Jacket + Umbrella")
    requests_seen = {}

    def post(url, **kwargs):
        requests_seen.update(url=url, **kwargs)
        return MockResponse(response_data)

    monkeypatch.setattr(frontend_app.requests, "post", post)

    result = frontend_app.fetch_recommendation("Kottayam", "Casual", "College", 50)

    assert result == response_data
    assert "ranked_outfits" not in result
    assert requests_seen["json"] == {
        "city": "Kottayam",
        "style": "Casual",
        "occasion": "Casual",
        "comfort_level": 50,
    }
    primary = frontend_app.get_primary_outfit(result, [])
    assert primary == {"name": "Light Jacket + Umbrella"}
    assert OUTFIT_AVATAR_FILES[primary["name"]] == "avatar_light_jacket.png"


def test_fetch_recommendation_preserves_catalog_ranking_and_primary(monkeypatch):
    ranked = [
        {"name": "Rain Jacket + Waterproof Shoes + Umbrella", "weather_match_score": 92},
        {"name": "Light Jacket + Umbrella", "weather_match_score": 76},
    ]
    response_data = weather_response(
        recommended_outfit="Light Jacket + Umbrella",
        ranked_outfits=ranked,
    )
    monkeypatch.setattr(
        frontend_app.requests,
        "post",
        lambda *args, **kwargs: MockResponse(response_data),
    )

    result = frontend_app.fetch_recommendation("Kottayam", "Casual", "College", 50)

    assert result["ranked_outfits"] == ranked
    assert frontend_app.get_primary_outfit(result, ranked) is ranked[1]


@pytest.mark.parametrize(
    "response_data, message",
    [
        (weather_response(recommended_outfit=42), "invalid recommended"),
        (
            weather_response(
                recommended_outfit="Light Jacket + Umbrella",
                ranked_outfits={"name": "Light Jacket + Umbrella"},
            ),
            "ranked_outfits",
        ),
        (
            weather_response(
                ranked_outfits=[{"weather_match_score": 90}],
            ),
            "invalid outfit",
        ),
        (
            {"city": "Kottayam", "current": [], "forecast": {}},
            "weather or forecast",
        ),
    ],
)
def test_fetch_recommendation_rejects_malformed_api_responses(monkeypatch, response_data, message):
    monkeypatch.setattr(
        frontend_app.requests,
        "post",
        lambda *args, **kwargs: MockResponse(response_data),
    )

    with pytest.raises(ValueError, match=message):
        frontend_app.fetch_recommendation("Kottayam", "Casual", "College", 50)


def test_fetch_recommendation_keeps_weather_when_outfit_is_empty(monkeypatch):
    response_data = weather_response(recommended_outfit="", ranked_outfits=[])
    monkeypatch.setattr(
        frontend_app.requests,
        "post",
        lambda *args, **kwargs: MockResponse(response_data),
    )

    result = frontend_app.fetch_recommendation("Kottayam", "Casual", "College", 50)

    assert result["forecast"]["rainfall"] == 32.7
    assert frontend_app.get_primary_outfit(result, []) is None


def test_fetch_recommendation_surfaces_api_errors_without_json(monkeypatch):
    monkeypatch.setattr(
        frontend_app.requests,
        "post",
        lambda *args, **kwargs: MockResponse(None, status_code=503),
    )

    with pytest.raises(ValueError, match="Unable to get recommendations"):
        frontend_app.fetch_recommendation("Kottayam", "Casual", "College", 50)
