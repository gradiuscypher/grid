import uuid
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field

from grid.api.deps import CurrentActor, DbSession, WriteActor
from grid.db.models import EntityType
from grid.services import entity_types as entity_type_service

router = APIRouter(prefix="/entity-types", tags=["entity-types"])


class EntityTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    display_name: str
    is_builtin: bool
    json_schema: dict[str, Any]
    icon: str | None
    color: str | None


class EntityTypeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str = Field(min_length=1, max_length=200)
    json_schema: dict[str, Any] = Field(default_factory=dict)
    icon: str | None = None
    color: str | None = None


class EntityTypeUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    json_schema: dict[str, Any] | None = None
    icon: str | None = None
    color: str | None = None


@router.get("", response_model=list[EntityTypeOut])
async def list_entity_types(actor: CurrentActor, db: DbSession) -> list[EntityType]:
    return await entity_type_service.list_entity_types(db)


@router.get("/{entity_type_id}", response_model=EntityTypeOut)
async def get_entity_type(
    entity_type_id: uuid.UUID, actor: CurrentActor, db: DbSession
) -> EntityType:
    return await entity_type_service.get_entity_type(db, entity_type_id=entity_type_id)


@router.post("", response_model=EntityTypeOut, status_code=status.HTTP_201_CREATED)
async def create_entity_type(
    body: EntityTypeCreateRequest, actor: WriteActor, db: DbSession
) -> EntityType:
    return await entity_type_service.create_entity_type(
        db,
        name=body.name,
        display_name=body.display_name,
        json_schema=body.json_schema,
        icon=body.icon,
        color=body.color,
    )


@router.patch("/{entity_type_id}", response_model=EntityTypeOut)
async def update_entity_type(
    entity_type_id: uuid.UUID, body: EntityTypeUpdateRequest, actor: WriteActor, db: DbSession
) -> EntityType:
    return await entity_type_service.update_entity_type(
        db,
        entity_type_id=entity_type_id,
        display_name=body.display_name,
        json_schema=body.json_schema,
        icon=body.icon,
        color=body.color,
    )


@router.delete("/{entity_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entity_type(entity_type_id: uuid.UUID, actor: WriteActor, db: DbSession) -> None:
    await entity_type_service.delete_entity_type(db, entity_type_id=entity_type_id)
