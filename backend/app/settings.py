import tomllib
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
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
    """All deploy-time knobs. Env vars use the FG_ prefix; `.env` is read too."""

    model_config = SettingsConfigDict(
        env_prefix="FG_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    database_path: Path = Path("data/funda-griller.sqlite")
    media_dir: Path = Path("data/media")
    affordability_rules_path: Path = CONFIG_DIR / "affordability.toml"
    flag_rules_path: Path = CONFIG_DIR / "flag_rules.toml"

    gemini_api_key: str | None = None
    vision_model: str | None = None
    verdict_model: str | None = None

    # Casefolded raw funda status string to normalised status.
    listing_status_map: dict[str, str] = Field(default_factory=dict)

    # Days after which a Source's facts count as Stale.
    source_ttl_days: dict[str, int] = Field(
        default_factory=lambda: {
            "energielabel": 365,
            "woz": 365,
            "flood_soil": 365,
            "noise": 365,
            "comparables": 14,
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
