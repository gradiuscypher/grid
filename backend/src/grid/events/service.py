import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from grid.db.models import CreatedVia, Event


async def record_event(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    actor_type: CreatedVia,
    actor_user_id: uuid.UUID | None = None,
    type: str,
    payload: dict[str, Any],
) -> Event:
    """Append a typed event row. Caller commits — this must run in the same
    transaction as the mutation it describes (ARCHITECTURE §4)."""
    event = Event(
        case_id=case_id,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        type=type,
        payload=payload,
    )
    db.add(event)
    await db.flush()
    return event
