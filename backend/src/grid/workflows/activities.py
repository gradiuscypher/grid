"""Temporal activities for `RunTransformWorkflow`. Activities do all the side
effects (DB access, credential decryption, transform invocation) — the workflow
itself only orchestrates them (CLAUDE.md Temporal discipline). Each activity opens
its own session since activities don't share the request-scoped session FastAPI
routes get.
"""

import uuid
from typing import Any

from temporalio import activity

from grid.core.config import get_settings
from grid.core.crypto import decrypt_credentials
from grid.db.models import EntityType, Node, Transform, TransformKind, TransformRun
from grid.db.session import async_session_maker
from grid.services import transforms as transform_service
from grid.transforms.registry import BUILTIN_TRANSFORMS
from grid.transforms.spec import RunRequest, RunResult, TransformInput


@activity.defn
async def mark_run_running_activity(run_id: str) -> None:
    async with async_session_maker() as db:
        await transform_service.mark_run_running(db, run_id=uuid.UUID(run_id))


@activity.defn
async def mark_run_failed_activity(run_id: str, error: str) -> None:
    async with async_session_maker() as db:
        await transform_service.mark_run_failed(db, run_id=uuid.UUID(run_id), error=error)


@activity.defn
async def prepare_invocation_activity(run_id: str) -> dict[str, Any]:
    """Decrypted credentials (never logged) + the manifest's `timeout_s`, which the
    workflow uses to size `invoke_transform_activity`'s `start_to_close_timeout` —
    read here, before that activity starts, since workflow code can't touch the DB
    itself to look it up directly."""
    async with async_session_maker() as db:
        run = await db.get(TransformRun, uuid.UUID(run_id))
        if run is None:
            raise ValueError(f"transform run {run_id} not found")
        transform = await db.get(Transform, run.transform_id)
        if transform is None:
            raise ValueError(f"transform {run.transform_id} not found")
        credentials: dict[str, str] = {}
        if transform.credentials_encrypted is not None:
            settings = get_settings()
            credentials = decrypt_credentials(
                transform.credentials_encrypted, key=settings.credential_key
            )
        return {"credentials": credentials, "timeout_s": transform.timeout_s}


@activity.defn
async def invoke_transform_activity(run_id: str, credentials: dict[str, str]) -> dict[str, Any]:
    async with async_session_maker() as db:
        run = await db.get(TransformRun, uuid.UUID(run_id))
        if run is None:
            raise ValueError(f"transform run {run_id} not found")
        transform = await db.get(Transform, run.transform_id)
        if transform is None:
            raise ValueError(f"transform {run.transform_id} not found")

        inputs: list[TransformInput] = []
        for node_id in run.input_node_ids:
            node = await db.get(Node, uuid.UUID(node_id))
            if node is None:
                continue
            entity_type = await db.get(EntityType, node.entity_type_id)
            if entity_type is None:
                continue
            inputs.append(
                TransformInput(type=entity_type.name, value=node.value, properties=node.properties)
            )

        request = RunRequest(inputs=inputs, params=run.params, credentials=credentials)

        if transform.kind == TransformKind.BUILTIN:
            builtin = BUILTIN_TRANSFORMS.get(transform.slug)
            if builtin is None:
                raise ValueError(f"builtin transform {transform.slug!r} is not registered in code")
            result: RunResult = await builtin.run(request)
            return result.model_dump(mode="json")

        # Remote (HTTP) transform invocation lands with registration in Phase 3b —
        # no remote transform can exist in the registry yet to reach this branch.
        raise NotImplementedError("remote transform execution lands in Phase 3b")


@activity.defn
async def merge_results_activity(run_id: str, result: dict[str, Any]) -> None:
    async with async_session_maker() as db:
        await transform_service.merge_transform_results(
            db, run_id=uuid.UUID(run_id), result=RunResult.model_validate(result)
        )
