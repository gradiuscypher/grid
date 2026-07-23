import uuid

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field

from grid.api.deps import CurrentActor, DbSession, WriteActor
from grid.db.models import Waypoint
from grid.services import waypoints as waypoint_service

router = APIRouter(prefix="/cases/{case_id}/waypoints", tags=["waypoints"])


class WaypointCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    position_x: float
    position_y: float
    zoom: float = 1.0


class WaypointUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    position_x: float | None = None
    position_y: float | None = None
    zoom: float | None = None


class WaypointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    name: str
    position_x: float
    position_y: float
    zoom: float
    created_by_user_id: uuid.UUID


@router.post("", response_model=WaypointOut, status_code=status.HTTP_201_CREATED)
async def create_waypoint(
    case_id: uuid.UUID, body: WaypointCreateRequest, actor: WriteActor, db: DbSession
) -> Waypoint:
    return await waypoint_service.create_waypoint(
        db,
        case_id=case_id,
        user=actor.user,
        name=body.name,
        position_x=body.position_x,
        position_y=body.position_y,
        zoom=body.zoom,
    )


@router.get("", response_model=list[WaypointOut])
async def list_waypoints(case_id: uuid.UUID, actor: CurrentActor, db: DbSession) -> list[Waypoint]:
    return await waypoint_service.list_waypoints(db, case_id=case_id, user=actor.user)


@router.get("/{waypoint_id}", response_model=WaypointOut)
async def get_waypoint(
    case_id: uuid.UUID, waypoint_id: uuid.UUID, actor: CurrentActor, db: DbSession
) -> Waypoint:
    return await waypoint_service.get_waypoint(
        db, case_id=case_id, waypoint_id=waypoint_id, user=actor.user
    )


@router.patch("/{waypoint_id}", response_model=WaypointOut)
async def update_waypoint(
    case_id: uuid.UUID,
    waypoint_id: uuid.UUID,
    body: WaypointUpdateRequest,
    actor: WriteActor,
    db: DbSession,
) -> Waypoint:
    return await waypoint_service.update_waypoint(
        db,
        case_id=case_id,
        waypoint_id=waypoint_id,
        user=actor.user,
        name=body.name,
        position_x=body.position_x,
        position_y=body.position_y,
        zoom=body.zoom,
    )


@router.delete("/{waypoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_waypoint(
    case_id: uuid.UUID, waypoint_id: uuid.UUID, actor: WriteActor, db: DbSession
) -> None:
    await waypoint_service.delete_waypoint(
        db, case_id=case_id, waypoint_id=waypoint_id, user=actor.user
    )
