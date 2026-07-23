import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grid.api.deps import DbSession
from grid.db.models import Event
from grid.events.manager import connection_manager
from grid.events.service import serialize_event
from grid.events.tickets import redeem_ticket
from grid.services.cases import get_role

router = APIRouter()


async def _replay(db: AsyncSession, *, case_id: uuid.UUID, since: int) -> list[dict[str, Any]]:
    result = await db.scalars(
        select(Event).where(Event.case_id == case_id, Event.seq > since).order_by(Event.seq)
    )
    return [serialize_event(event) for event in result]


@router.websocket("/ws/cases/{case_id}")
async def case_events(
    websocket: WebSocket, case_id: uuid.UUID, db: DbSession, ticket: str, since: int = 0
) -> None:
    """Ticket-authenticated (see events/tickets.py) event stream for a case:
    replays the backlog since `since`, then streams live events until the
    client disconnects. Presence (cursors/selections) is Phase 5 scope."""
    user_id = redeem_ticket(ticket)
    if user_id is None:
        await websocket.close(code=4401)
        return

    role = await get_role(db, case_id=case_id, user_id=user_id)
    if role is None:
        await websocket.close(code=4403)
        return
    backlog = await _replay(db, case_id=case_id, since=since)

    await websocket.accept()
    for message in backlog:
        await websocket.send_json(message)

    connection_manager.subscribe(case_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.unsubscribe(case_id, websocket)
