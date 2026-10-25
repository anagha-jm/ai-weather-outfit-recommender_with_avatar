from pathlib import Path

from frontend import app as frontend_app


def test_validate_email_rules_and_auth_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(frontend_app, "AUTH_DB_PATH", tmp_path / "dina_auth.db")
    frontend_app.init_auth_store()

    assert frontend_app.validate_email("user@example.com") is True
    assert frontend_app.validate_email("not-an-email") is False

    created = frontend_app.create_user_account(
        email="new.user@example.com",
        password="StrongPass123!",
        display_name="Alicia",
    )
    assert created is True

    user = frontend_app.authenticate_user("new.user@example.com", "StrongPass123!")
    assert user is not None
    assert user["email"] == "new.user@example.com"
    assert user["display_name"] == "Alicia"

    assert frontend_app.authenticate_user("new.user@example.com", "WrongPass123!") is False
