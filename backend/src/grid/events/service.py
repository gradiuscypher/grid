import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from grid.db.models import CreatedVia, Event

# Single shared NOTIFY channel; every payload carries its own case_id so one
# listener connection can fan out to every case (ARCHITECTURE §4).
EVENTS_CHANNEL = "grid_case_events"


async def record_event(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    actor_type: CreatedVia,
    actor_user_id: uuid.UUID | None = None,
    actor_transform_run_id: uuid.UUID | None = None,
    type: str,
    payload: dict[str, Any],
) -> Event:
    """Append a typed event row and queue a pg NOTIFY. Caller commits — both the
    row and the NOTIFY only become visible to listeners once that commit lands,
    so this must run in the same transaction as the mutation it describes."""
    event = Event(
        case_id=case_id,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        actor_transform_run_id=actor_transform_run_id,
        type=type,
        payload=payload,
    )
    db.add(event)
    await db.flush()
    await db.execute(
        text("SELECT pg_notify(:channel, :notify_payload)"),
        {
            "channel": EVENTS_CHANNEL,
            "notify_payload": json.dumps({"case_id": str(case_id), "seq": event.seq}),
        },
    )
    return event


def serialize_event(event: Event) -> dict[str, Any]:
    """Shared wire shape for both the replay backlog and the live broadcast."""
    return {
        "seq": event.seq,
        "case_id": str(event.case_id),
        "type": event.type,
        "actor_type": event.actor_type.value,
        "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
        "actor_transform_run_id": (
            str(event.actor_transform_run_id) if event.actor_transform_run_id else None
        ),
        "payload": event.payload,
        "created_at": event.created_at.isoformat(),
    }
