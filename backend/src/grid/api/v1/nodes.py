import uuid
from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, ConfigDict, Field

from grid.api.deps import CurrentActor, DbSession, WriteActor
from grid.db.models import CreatedVia, Node
from grid.services import nodes as node_service

router = APIRouter(prefix="/cases/{case_id}/nodes", tags=["nodes"])


class NodeCreateRequest(BaseModel):
    entity_type_id: uuid.UUID
    value: str = Field(min_length=1, max_length=2000)
    properties: dict[str, Any] = Field(default_factory=dict)
    position_x: float = 0.0
    position_y: float = 0.0
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class NodeUpdateRequest(BaseModel):
    properties: dict[str, Any] | None = None
    position_x: float | None = None
    position_y: float | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    entity_type_id: uuid.UUID
    value: str
    canonical_value: str
    properties: dict[str, Any]
    position_x: float
    position_y: float
    confidence: float
    created_via: CreatedVia
    created_by_user_id: uuid.UUID | None


@router.post("", response_model=NodeOut)
async def create_node(
    case_id: uuid.UUID,
    body: NodeCreateRequest,
    actor: WriteActor,
    db: DbSession,
    response: Response,
) -> Node:
    node, created = await node_service.create_node(
        db,
        case_id=case_id,
        user=actor.user,
        entity_type_id=body.entity_type_id,
        value=body.value,
        properties=body.properties,
        position_x=body.position_x,
        position_y=body.position_y,
        confidence=body.confidence,
    )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return node


@router.get("", response_model=list[NodeOut])
async def list_nodes(case_id: uuid.UUID, actor: CurrentActor, db: DbSession) -> list[Node]:
    return await node_service.list_nodes(db, case_id=case_id, user=actor.user)


@router.get("/{node_id}", response_model=NodeOut)
async def get_node(
    case_id: uuid.UUID, node_id: uuid.UUID, actor: CurrentActor, db: DbSession
) -> Node:
    return await node_service.get_node(db, case_id=case_id, node_id=node_id, user=actor.user)


@router.patch("/{node_id}", response_model=NodeOut)
async def update_node(
    case_id: uuid.UUID,
    node_id: uuid.UUID,
    body: NodeUpdateRequest,
    actor: WriteActor,
    db: DbSession,
) -> Node:
    return await node_service.update_node(
        db,
        case_id=case_id,
        node_id=node_id,
        user=actor.user,
        properties=body.properties,
        position_x=body.position_x,
        position_y=body.position_y,
        confidence=body.confidence,
    )


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    case_id: uuid.UUID, node_id: uuid.UUID, actor: WriteActor, db: DbSession
) -> None:
    await node_service.delete_node(db, case_id=case_id, node_id=node_id, user=actor.user)
