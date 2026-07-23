"""Background task: one dedicated Postgres connection LISTENs on the events
channel and fans notified rows out to in-process WS subscribers via
`connection_manager`. Runs for the lifetime of the API process (see main.py's
lifespan) — this is the cross-process half of realtime; `manager.py` is the
in-process half.
"""

import asyncio
import json
import logging
import uuid

import psycopg
from sqlalchemy import make_url, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from grid.core.config import get_settings
from grid.db.models import Event
from grid.db.session import engine
from grid.events.manager import connection_manager
from grid.events.service import EVENTS_CHANNEL, serialize_event

logger = logging.getLogger(__name__)

_session_maker = async_sessionmaker(engine, expire_on_commit=False)


def _listen_dsn() -> str:
    # psycopg's raw AsyncConnection wants a plain postgresql:// DSN, not
    # SQLAlchemy's "+psycopg" driver-qualified URL.
    return (
        make_url(get_settings().database_url)
        .set(drivername="postgresql")
        .render_as_string(hide_password=False)
    )


async def _dispatch(raw_payload: str) -> None:
    data = json.loads(raw_payload)
    case_id = uuid.UUID(data["case_id"])
    seq = data["seq"]
    async with _session_maker() as session:
        event = await session.scalar(select(Event).where(Event.seq == seq))
    if event is None:
        return
    await connection_manager.broadcast(case_id, serialize_event(event))


async def run_listener() -> None:
    dsn = _listen_dsn()
    while True:
        try:
            async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
                await conn.execute(f"LISTEN {EVENTS_CHANNEL}")
                async for notify in conn.notifies():
                    await _dispatch(notify.payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("case-events listener connection dropped, retrying")
            await asyncio.sleep(1)
