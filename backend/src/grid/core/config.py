from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GRID_", env_file=".env", extra="ignore")

    database_url: str = Field(
        validation_alias="DATABASE_URL",
        default="postgresql+psycopg://grid:grid@localhost:5432/grid",
    )

    session_cookie_name: str = "grid_session"
    session_ttl_hours: int = 24 * 14
    # Custom-header requirement (ARCHITECTURE §5) mitigates CSRF: cross-site form
    # submissions and simple cross-origin fetches can't set arbitrary headers.
    client_header_name: str = "X-Grid-Client"

    # False in dev (plain HTTP over docker compose); prod (behind Caddy/TLS) sets
    # GRID_COOKIE_SECURE=true.
    cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
