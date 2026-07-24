import uuid
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict

from grid.api.deps import CurrentActor, DbSession
from grid.db.models import Transform, TransformKind
from grid.services import transforms as transform_service

router = APIRouter(prefix="/transforms", tags=["transforms"])


class TransformOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    kind: TransformKind
    name: str
    version: str
    description: str
    input_types: list[str]
    output_types: list[str]
    params_schema: dict[str, Any]
    credential_names: list[str]
    timeout_s: int
    rate_limit: int | None
    is_enabled: bool


@router.get("", response_model=list[TransformOut], operation_id="list_transforms")
async def list_transforms(
    actor: CurrentActor,
    db: DbSession,
    input_type: str | None = Query(default=None),
) -> list[Transform]:
    return await transform_service.list_transforms(db, input_type=input_type)


@router.get("/{transform_id}", response_model=TransformOut, operation_id="get_transform")
async def get_transform(transform_id: uuid.UUID, actor: CurrentActor, db: DbSession) -> Transform:
    return await transform_service.get_transform(db, transform_id=transform_id)
