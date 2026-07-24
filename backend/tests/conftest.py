from collections.abc import AsyncGenerator, Awaitable, Callable

import httpx
import pytest
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from grid.core.config import get_settings
from grid.db.models import Base, EntityType
from grid.db.session import get_session
from grid.main import app
from grid.services.transforms import sync_builtin_transforms

# Mirrors the `244e9746d9db` data migration's BUILTINS (ARCHITECTURE §3) — kept as
# a separate literal rather than importing the versions module, matching
# tests/db/test_migrations.py's existing precedent (module name isn't a valid
# Python identifier, and versions/ is excluded from normal imports by design).
_BUILTIN_ENTITY_TYPES: list[tuple[str, str, str, str]] = [
    ("domain", "Domain", "globe", "#4f8cff"),
    ("hostname", "Hostname", "server", "#4f8cff"),
    ("ipv4", "IPv4 Address", "hard-drive", "#22a06b"),
    ("ipv6", "IPv6 Address", "hard-drive", "#22a06b"),
    ("cidr", "CIDR Block", "network", "#22a06b"),
    ("asn", "ASN", "share-2", "#22a06b"),
    ("url", "URL", "link", "#a855f7"),
    ("email", "Email Address", "mail", "#f59e0b"),
    ("username", "Username", "at-sign", "#f59e0b"),
    ("person", "Person", "user", "#ef4444"),
    ("organization", "Organization", "building", "#ef4444"),
    ("hash", "Hash", "hash", "#6b7280"),
    ("note", "Note", "file-text", "#eab308"),
]


def _test_db_url(base_url: str) -> str:
    url = make_url(base_url)
    return url.set(database=f"{url.database}_test").render_as_string(hide_password=False)


def _ensure_database_exists(base_url: str, dbname: str) -> None:
    """Real integration tests need a real Postgres — create a disposable `_test`
    sibling database (idempotent) rather than running against the dev database."""
    admin_url = make_url(base_url).set(drivername="postgresql+psycopg")
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": dbname}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    engine.dispose()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    base_url = get_settings().database_url
    test_url = _test_db_url(base_url)
    _ensure_database_exists(base_url, make_url(test_url).database or "grid_test")
    return test_url


async def _seed_builtin_entity_types(session: AsyncSession) -> None:
    """Mirrors the `244e9746d9db` data migration — `create_all` (unlike a real
    `alembic upgrade head`) skips data migrations, so tests need this done by hand
    to see the same builtins dev/prod always have."""
    session.add_all(
        EntityType(
            name=name,
            display_name=display_name,
            is_builtin=True,
            json_schema={"type": "object"},
            icon=icon,
            color=color,
        )
        for name, display_name, icon, color in _BUILTIN_ENTITY_TYPES
    )
    await session.commit()


@pytest.fixture(scope="session")
async def test_engine(test_database_url: str) -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(test_database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        await _seed_builtin_entity_types(session)
        await sync_builtin_transforms(session)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """One test = one outer transaction, rolled back at teardown. Session-level
    commits become savepoints so service-layer code can commit freely in tests."""
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        session_maker = async_sessionmaker(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with session_maker() as session:
            yield session
        await trans.rollback()


@pytest.fixture
async def api_client_factory(
    db_session: AsyncSession,
) -> AsyncGenerator[Callable[[], Awaitable[httpx.AsyncClient]]]:
    """Each call returns a new client (own cookie jar, i.e. own "browser") bound
    to the *same* test transaction, so multi-actor tests (owner + invited viewer)
    see each other's writes without needing separate DB fixtures per actor."""

    async def _override_get_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    settings = get_settings()
    clients: list[httpx.AsyncClient] = []

    async def _make() -> httpx.AsyncClient:
        transport = httpx.ASGITransport(app=app)
        client = httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={settings.client_header_name: "1"},
        )
        clients.append(client)
        return client

    yield _make

    for client in clients:
        await client.aclose()
    app.dependency_overrides.clear()


@pytest.fixture
async def api_client(
    api_client_factory: Callable[[], Awaitable[httpx.AsyncClient]],
) -> httpx.AsyncClient:
    return await api_client_factory()
