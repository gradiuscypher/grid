import uuid
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field

from grid.api.deps import CurrentActor, DbSession, WriteActor
from grid.db.models import TransformRun, TransformRunStatus
from grid.services import transforms as transform_service
from grid.workflows.launch import launch_transform_run

router = APIRouter(prefix="/cases/{case_id}/transform-runs", tags=["transform-runs"])


class TransformRunCreateRequest(BaseModel):
    transform_id: uuid.UUID
    input_node_ids: list[uuid.UUID] = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class TransformRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    transform_id: uuid.UUID
    status: TransformRunStatus
    triggered_by_user_id: uuid.UUID
    input_node_ids: list[str]
    params: dict[str, Any]
    result_node_ids: list[str]
    result_edge_ids: list[str]
    logs: list[str]
    error: str | None
    temporal_workflow_id: str | None


@router.post(
    "",
    response_model=TransformRunOut,
    status_code=status.HTTP_201_CREATED,
    operation_id="run_transform",
)
async def run_transform(
    case_id: uuid.UUID, body: TransformRunCreateRequest, actor: WriteActor, db: DbSession
) -> TransformRun:
    return await launch_transform_run(
        db,
        case_id=case_id,
        transform_id=body.transform_id,
        input_node_ids=body.input_node_ids,
        params=body.params,
        user=actor.user,
    )


@router.get("", response_model=list[TransformRunOut], operation_id="list_transform_runs")
async def list_transform_runs(
    case_id: uuid.UUID, actor: CurrentActor, db: DbSession
) -> list[TransformRun]:
    return await transform_service.list_transform_runs(db, case_id=case_id, user=actor.user)


@router.get("/{run_id}", response_model=TransformRunOut, operation_id="get_transform_run")
async def get_transform_run(
    case_id: uuid.UUID, run_id: uuid.UUID, actor: CurrentActor, db: DbSession
) -> TransformRun:
    return await transform_service.get_transform_run(
        db, case_id=case_id, run_id=run_id, user=actor.user
    )
