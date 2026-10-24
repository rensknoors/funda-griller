from app.settings import Settings


def test_models_keys_and_source_ttls_come_from_environment(monkeypatch):
    monkeypatch.setenv("FG_GEMINI_API_KEY", "key-123")
    monkeypatch.setenv("FG_VISION_MODEL", "vision-x")
    monkeypatch.setenv("FG_VERDICT_MODEL", "verdict-y")
    monkeypatch.setenv("FG_SOURCE_TTL_DAYS__WOZ", "42")

    settings = Settings(_env_file=None)

    assert settings.gemini_api_key == "key-123"
    assert settings.vision_model == "vision-x"
    assert settings.verdict_model == "verdict-y"
    assert settings.source_ttl_days["woz"] == 42


def test_source_ttl_defaults_cover_every_source(monkeypatch):
    settings = Settings(_env_file=None)

    assert set(settings.source_ttl_days) == {
        "energielabel",
        "woz",
        "flood_soil",
        "noise",
        "comparables",
    }


def test_models_and_status_map_default_from_config_file(monkeypatch):
    monkeypatch.delenv("FG_VISION_MODEL", raising=False)
    monkeypatch.delenv("FG_VERDICT_MODEL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.vision_model == "gemini-3.8-flash"
    assert settings.verdict_model == "gemini-3.8-flash"
    assert settings.listing_status_map["onder bod"] == "negotiations"


def test_environment_overrides_config_file_defaults(monkeypatch):
    monkeypatch.setenv("FG_VISION_MODEL", "vision-x")

    settings = Settings(_env_file=None)

    assert settings.vision_model == "vision-x"
    assert settings.verdict_model == "gemini-3.8-flash"
