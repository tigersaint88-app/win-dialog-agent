"""Runtime configuration / 运行时配置.

All timeouts and retry counts come from settings (env / .env), never hard-coded
call sites. 所有超时与重试次数走配置，调用处不硬编码。
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurable knobs for dialog automation."""

    model_config = SettingsConfigDict(
        env_prefix="WIN_DIALOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    default_timeout: float = Field(default=10.0, description="Seconds to wait for a dialog")
    retry_count: int = Field(default=3, ge=0, description="UIA lookup retries")
    retry_delay: float = Field(default=0.3, ge=0.0, description="Seconds between retries")
    overwrite_confirm_timeout: float = Field(
        default=2.0,
        description="Seconds to wait for overwrite / secondary confirm dialog",
    )
    log_level: str = Field(default="INFO", description="Logging level")
    standard_class_name: str = Field(default="#32770", description="Win32 common dialog class")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear settings cache (tests)."""
    get_settings.cache_clear()
