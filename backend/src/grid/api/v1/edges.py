import uuid
from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, ConfigDict, Field

from grid.api.deps import CurrentActor, DbSession, WriteActor
from grid.db.models import CreatedVia, Edge
from grid.services import edges as edge_service

router = APIRouter(prefix="/cases/{case_id}/edges", tags=["edges"])


class EdgeCreateRequest(BaseModel):
    src_node_id: uuid.UUID
    dst_node_id: uuid.UUID
    relationship: str = Field(min_length=1, max_length=200)
    label: str | None = Field(default=None, max_length=200)
    properties: dict[str, Any] = Field(default_factory=dict)


class EdgeUpdateRequest(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    properties: dict[str, Any] | None = None


class EdgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    src_node_id: uuid.UUID
    dst_node_id: uuid.UUID
    relationship: str
    label: str | None
    properties: dict[str, Any]
    created_via: CreatedVia
    created_by_user_id: uuid.UUID | None


@router.post("", response_model=EdgeOut)
async def create_edge(
    case_id: uuid.UUID,
    body: EdgeCreateRequest,
    actor: WriteActor,
    db: DbSession,
    response: Response,
) -> Edge:
    edge, created = await edge_service.create_edge(
        db,
        case_id=case_id,
        user=actor.user,
        src_node_id=body.src_node_id,
        dst_node_id=body.dst_node_id,
        relationship=body.relationship,
        label=body.label,
        properties=body.properties,
    )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return edge


@router.get("", response_model=list[EdgeOut])
async def list_edges(case_id: uuid.UUID, actor: CurrentActor, db: DbSession) -> list[Edge]:
    return await edge_service.list_edges(db, case_id=case_id, user=actor.user)


@router.get("/{edge_id}", response_model=EdgeOut)
async def get_edge(
    case_id: uuid.UUID, edge_id: uuid.UUID, actor: CurrentActor, db: DbSession
) -> Edge:
    return await edge_service.get_edge(db, case_id=case_id, edge_id=edge_id, user=actor.user)


@router.patch("/{edge_id}", response_model=EdgeOut)
async def update_edge(
    case_id: uuid.UUID,
    edge_id: uuid.UUID,
    body: EdgeUpdateRequest,
    actor: WriteActor,
    db: DbSession,
) -> Edge:
    return await edge_service.update_edge(
        db,
        case_id=case_id,
        edge_id=edge_id,
        user=actor.user,
        label=body.label,
        properties=body.properties,
    )


@router.delete("/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edge(
    case_id: uuid.UUID, edge_id: uuid.UUID, actor: WriteActor, db: DbSession
) -> None:
    await edge_service.delete_edge(db, case_id=case_id, edge_id=edge_id, user=actor.user)
