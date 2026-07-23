import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, make_url, text

from grid.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]

BUILTIN_ENTITY_TYPE_NAMES = {
    "domain",
    "hostname",
    "ipv4",
    "ipv6",
    "cidr",
    "asn",
    "url",
    "email",
    "username",
    "person",
    "organization",
    "hash",
    "note",
}


@pytest.fixture
def migration_database_url() -> Generator[str]:
    """A short-lived database driven purely through Alembic (not create_all), so
    this test exercises exactly what `make migrate` runs in dev/CI/prod."""
    base = make_url(get_settings().database_url).set(drivername="postgresql+psycopg")
    dbname = f"grid_migration_test_{uuid.uuid4().hex[:8]}"

    admin_engine = create_engine(base, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    admin_engine.dispose()

    yield base.set(database=dbname).render_as_string(hide_password=False)

    admin_engine = create_engine(base, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE "{dbname}"'))
    admin_engine.dispose()


def _config_for(database_url: str) -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


# Deliberately a sync test: Alembic's env.py drives its own asyncio.run() per
# command, which must not run inside a pytest-asyncio event loop.
def test_migrations_seed_builtins_and_roundtrip(migration_database_url: str) -> None:
    cfg = _config_for(migration_database_url)

    command.upgrade(cfg, "head")

    engine = create_engine(migration_database_url)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT name, is_builtin FROM entity_types")).fetchall()
    engine.dispose()

    assert {row.name for row in rows} == BUILTIN_ENTITY_TYPE_NAMES
    assert all(row.is_builtin for row in rows)

    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
