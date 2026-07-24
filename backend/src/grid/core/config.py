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

    temporal_address: str = Field(validation_alias="TEMPORAL_ADDRESS", default="localhost:7233")
    temporal_task_queue: str = "grid-transforms"

    # Fernet key for the credential vault (transform creds at rest, ARCHITECTURE §6).
    # This default is a fixed dev-only key so `make dev` works with no .env — prod
    # MUST override GRID_CREDENTIAL_KEY (see .env.example). Never used to encrypt
    # anything sensitive outside a throwaway dev stack.
    credential_key: str = "jXAOl5PJA_14ZLxLV24UULyVhNqQxPOjxRkchYFxbiQ="


@lru_cache
def get_settings() -> Settings:
    return Settings()
