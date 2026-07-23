import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.errors import NotFoundError
from grid.db.models import CaseRole, CreatedVia, User, Waypoint
from grid.events.service import record_event
from grid.services.cases import require_role


async def create_waypoint(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    user: User,
    name: str,
    position_x: float,
    position_y: float,
    zoom: float = 1.0,
) -> Waypoint:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    waypoint = Waypoint(
        case_id=case_id,
        name=name,
        position_x=position_x,
        position_y=position_y,
        zoom=zoom,
        created_by_user_id=user.id,
    )
    db.add(waypoint)
    await db.flush()
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="waypoint.created",
        payload={"waypoint_id": str(waypoint.id), "name": name},
    )
    await db.commit()
    await db.refresh(waypoint)
    return waypoint


async def get_waypoint(
    db: AsyncSession, *, case_id: uuid.UUID, waypoint_id: uuid.UUID, user: User
) -> Waypoint:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    waypoint = await db.get(Waypoint, waypoint_id)
    if waypoint is None or waypoint.case_id != case_id:
        raise NotFoundError("waypoint not found")
    return waypoint


async def list_waypoints(db: AsyncSession, *, case_id: uuid.UUID, user: User) -> list[Waypoint]:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    result = await db.scalars(select(Waypoint).where(Waypoint.case_id == case_id))
    return list(result)


async def update_waypoint(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    waypoint_id: uuid.UUID,
    user: User,
    name: str | None = None,
    position_x: float | None = None,
    position_y: float | None = None,
    zoom: float | None = None,
) -> Waypoint:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    waypoint = await get_waypoint(db, case_id=case_id, waypoint_id=waypoint_id, user=user)
    if name is not None:
        waypoint.name = name
    if position_x is not None:
        waypoint.position_x = position_x
    if position_y is not None:
        waypoint.position_y = position_y
    if zoom is not None:
        waypoint.zoom = zoom
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="waypoint.updated",
        payload={"waypoint_id": str(waypoint.id)},
    )
    await db.commit()
    await db.refresh(waypoint)
    return waypoint


async def delete_waypoint(
    db: AsyncSession, *, case_id: uuid.UUID, waypoint_id: uuid.UUID, user: User
) -> None:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    waypoint = await get_waypoint(db, case_id=case_id, waypoint_id=waypoint_id, user=user)
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="waypoint.deleted",
        payload={"waypoint_id": str(waypoint.id)},
    )
    await db.delete(waypoint)
    await db.commit()
