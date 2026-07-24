"""API-facing entrypoint for starting a transform run: creates the `TransformRun`
row via the service layer, then starts `RunTransformWorkflow`. Kept out of
`services/transforms.py` so that module stays free of a Temporal client dependency
— only this thin layer needs it.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.config import get_settings
from grid.core.temporal_client import get_temporal_client
from grid.db.models import TransformRun, User
from grid.services import transforms as transform_service


async def launch_transform_run(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    transform_id: uuid.UUID,
    input_node_ids: list[uuid.UUID],
    params: dict[str, Any] | None,
    user: User,
) -> TransformRun:
    """If Temporal itself is unreachable, the run is marked failed rather than left
    stuck `PENDING` — the request still succeeds (the run was validly created), the
    client just sees it land in `failed` with a clear error."""
    run = await transform_service.start_transform_run(
        db,
        case_id=case_id,
        transform_id=transform_id,
        input_node_ids=input_node_ids,
        params=params,
        user=user,
    )

    settings = get_settings()
    workflow_id = f"transform-run-{run.id}"
    try:
        client = await get_temporal_client()
        await client.start_workflow(
            "RunTransformWorkflow",
            str(run.id),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
    except Exception as exc:
        await transform_service.mark_run_failed(
            db, run_id=run.id, error=f"could not start workflow: {exc}"
        )
        await db.refresh(run)
        return run

    run.temporal_workflow_id = workflow_id
    await db.commit()
    await db.refresh(run)
    return run
