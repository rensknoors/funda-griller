import tomllib
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"
# Absolute, so the backend finds them whatever directory it runs from; the later file wins.
ENV_FILES = (REPO_ROOT / ".env", REPO_ROOT / "backend" / ".env")
DEFAULTS_FILE = CONFIG_DIR / "defaults.toml"


class _DefaultsFileSource(PydanticBaseSettingsSource):
    """Lowest-priority source: repo-level `config/defaults.toml`."""

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        with DEFAULTS_FILE.open("rb") as f:
            data = tomllib.load(f)
        return {
            **data.get("llm", {}),
            "listing_status_map": data.get("listing_status_map", {}),
        }


class Settings(BaseSettings):
    """All deploy-time knobs. Env vars use the FG_ prefix; `.env` at the repo root and in backend/ are read too."""

    model_config = SettingsConfigDict(
        env_prefix="FG_",
        env_file=ENV_FILES,
        env_nested_delimiter="__",
        extra="ignore",
    )

    database_path: Path = Path("data/funda-griller.sqlite")
    media_dir: Path = Path("data/media")
    affordability_rules_path: Path = CONFIG_DIR / "affordability.toml"
    flag_rules_path: Path = CONFIG_DIR / "flag_rules.toml"

    gemini_api_key: str | None = None
    # RVO EP-Online API key for the energielabel register; without it that Source is skipped.
    ep_online_api_key: str | None = None
    # OpenRouteService API key for commute travel times; without it the commute Source is skipped.
    openrouteservice_api_key: str | None = None
    vision_model: str | None = None
    verdict_model: str | None = None

    # Casefolded raw funda status string to normalised status.
    listing_status_map: dict[str, str] = Field(default_factory=dict)

    # Comparables: at most this many follow-up provider fetches per user request; fewer usable
    # comparables than the minimum count as thin.
    comparables_max_fetches: int = 5
    comparables_min_count: int = 3
    # The derived Walk-away Maximum sits this share above what sufficient comparables put the house
    # at, or, when comparables are thin or missing, this share above the asking price (never above
    # what the household can afford).
    walk_away_comparables_premium: float = 0.10
    walk_away_asking_price_margin: float = 0.05

    # Days after which a Source's facts count as Stale.
    source_ttl_days: dict[str, int] = Field(
        default_factory=lambda: {
            "energielabel": 365,
            "woz": 365,
            "flood_soil": 365,
            "noise": 365,
            "comparables": 14,
            "commute": 180,
        }
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            _DefaultsFileSource(settings_cls),
        )
