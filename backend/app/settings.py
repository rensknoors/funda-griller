from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    cors_origins: list[str] = ["http://localhost:5173"]

    gemini_api_key: str | None = None
    vision_model: str | None = None
    verdict_model: str | None = None

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
