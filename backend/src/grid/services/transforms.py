"""Transform registry + run lifecycle (ARCHITECTURE §6). `sync_builtin_transforms`
keeps the `transforms` table in sync with code-defined descriptors; the rest of
this module is the service-layer half of `RunTransformWorkflow` — everything the
API needs to start a run, and everything the Temporal activities need to update
one as it progresses (`workflows/activities.py` calls the `mark_run_*` and
`merge_transform_results` functions with its own per-activity session).
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.errors import NotFoundError, ValidationError
from grid.db.models import (
    CaseRole,
    CreatedVia,
    EntityType,
    Node,
    Transform,
    TransformKind,
    TransformRun,
    TransformRunStatus,
    User,
)
from grid.events.service import record_event
from grid.services import edges as edge_service
from grid.services import nodes as node_service
from grid.services.canonicalize import canonicalize
from grid.services.cases import require_role
from grid.transforms.registry import BUILTIN_TRANSFORMS
from grid.transforms.spec import RunResult


async def sync_builtin_transforms(db: AsyncSession) -> None:
    """Idempotent upsert of the code-defined builtin registry. Called at API and
    worker process startup so `transforms` always mirrors what's actually
    runnable in this build, without a migration per builtin change (unlike
    entity types, whose builtins are static seed data)."""
    for transform in BUILTIN_TRANSFORMS.values():
        d = transform.descriptor
        existing = await db.scalar(select(Transform).where(Transform.slug == d.id))
        if existing is None:
            existing = Transform(slug=d.id, kind=TransformKind.BUILTIN)
            db.add(existing)
        existing.kind = TransformKind.BUILTIN
        existing.name = d.name
        existing.version = d.version
        existing.description = d.description
        existing.input_types = d.input_types
        existing.output_types = d.output_types
        existing.params_schema = d.params_schema
        existing.credential_names = d.credentials
        existing.timeout_s = d.timeout_s
        existing.rate_limit = d.rate_limit
    await db.commit()


async def list_transforms(db: AsyncSession, *, input_type: str | None = None) -> list[Transform]:
    result = await db.scalars(
        select(Transform).where(Transform.is_enabled).order_by(Transform.name)
    )
    transforms = list(result)
    if input_type is not None:
        transforms = [t for t in transforms if input_type in t.input_types]
    return transforms


async def get_transform(db: AsyncSession, *, transform_id: uuid.UUID) -> Transform:
    transform = await db.get(Transform, transform_id)
    if transform is None:
        raise NotFoundError("transform not found")
    return transform


async def start_transform_run(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    transform_id: uuid.UUID,
    input_node_ids: list[uuid.UUID],
    params: dict[str, Any] | None,
    user: User,
) -> TransformRun:
    """Validates and creates the `TransformRun` row (`PENDING`). Does not start the
    Temporal workflow — that's `workflows.launch.launch_transform_run`, which wraps
    this with the actual `client.start_workflow` call so this module stays free of
    a dependency on the Temporal client."""
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    transform = await get_transform(db, transform_id=transform_id)
    if not transform.is_enabled:
        raise ValidationError(f"transform {transform.slug!r} is disabled")
    if not input_node_ids:
        raise ValidationError("at least one input node is required")

    nodes: list[Node] = []
    for node_id in input_node_ids:
        node = await db.get(Node, node_id)
        if node is None or node.case_id != case_id:
            raise ValidationError(f"node {node_id} does not exist in this case")
        nodes.append(node)

    entity_type_ids = {n.entity_type_id for n in nodes}
    entity_type_names = {
        et.id: et.name
        for et in await db.scalars(select(EntityType).where(EntityType.id.in_(entity_type_ids)))
    }
    for node in nodes:
        type_name = entity_type_names[node.entity_type_id]
        if type_name not in transform.input_types:
            raise ValidationError(
                f"transform {transform.slug!r} does not accept input type {type_name!r}"
            )

    run = TransformRun(
        case_id=case_id,
        transform_id=transform_id,
        status=TransformRunStatus.PENDING,
        triggered_by_user_id=user.id,
        input_node_ids=[str(n.id) for n in nodes],
        params=params or {},
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def get_transform_run(
    db: AsyncSession, *, case_id: uuid.UUID, run_id: uuid.UUID, user: User
) -> TransformRun:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    run = await db.get(TransformRun, run_id)
    if run is None or run.case_id != case_id:
        raise NotFoundError("transform run not found")
    return run


async def list_transform_runs(
    db: AsyncSession, *, case_id: uuid.UUID, user: User
) -> list[TransformRun]:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    result = await db.scalars(
        select(TransformRun)
        .where(TransformRun.case_id == case_id)
        .order_by(TransformRun.created_at.desc())
    )
    return list(result)


async def mark_run_running(db: AsyncSession, *, run_id: uuid.UUID) -> None:
    run = await db.get(TransformRun, run_id)
    if run is None:
        raise NotFoundError("transform run not found")
    run.status = TransformRunStatus.RUNNING
    await record_event(
        db,
        case_id=run.case_id,
        actor_type=CreatedVia.TRANSFORM,
        actor_transform_run_id=run.id,
        type="transform_run.started",
        payload={"transform_run_id": str(run.id), "transform_id": str(run.transform_id)},
    )
    await db.commit()


async def mark_run_failed(db: AsyncSession, *, run_id: uuid.UUID, error: str) -> None:
    run = await db.get(TransformRun, run_id)
    if run is None:
        return
    run.status = TransformRunStatus.FAILED
    run.error = error[:4000]
    await record_event(
        db,
        case_id=run.case_id,
        actor_type=CreatedVia.TRANSFORM,
        actor_transform_run_id=run.id,
        type="transform_run.failed",
        payload={"transform_run_id": str(run.id), "error": run.error},
    )
    await db.commit()


async def merge_transform_results(
    db: AsyncSession, *, run_id: uuid.UUID, result: RunResult
) -> TransformRun:
    """Turns a transform's `(type, value)`-addressed result into real nodes/edges
    via the normal node/edge services — same dedup, same provenance rules, same
    events as a human editing the graph, just with `created_via=TRANSFORM`.

    Deliberately not one giant transaction: `create_node`/`create_edge` each
    commit their own row + event, same as when called from the API. That costs
    all-or-nothing atomicity across the whole result set, but buys something
    more useful for a Temporal activity — structural dedup means a retried
    merge (crash mid-way, activity retry policy) just re-resolves already-created
    nodes/edges instead of erroring or duplicating them.
    """
    run = await db.get(TransformRun, run_id)
    if run is None:
        raise NotFoundError("transform run not found")
    triggering_user = await db.get(User, run.triggered_by_user_id)
    if triggering_user is None:
        raise NotFoundError("triggering user not found")

    entity_types_by_name = {et.name: et for et in await db.scalars(select(EntityType))}

    # Seed the (type, canonical_value) -> node lookup with the run's own inputs so
    # a result edge can reference an input entity without the transform having to
    # re-describe it as a "new" node.
    node_lookup: dict[tuple[str, str], Node] = {}
    for node_id in run.input_node_ids:
        node = await db.get(Node, uuid.UUID(node_id))
        if node is None:
            continue
        entity_type = await db.get(EntityType, node.entity_type_id)
        if entity_type is not None:
            node_lookup[(entity_type.name, node.canonical_value)] = node

    logs = list(run.logs)
    result_node_ids: list[str] = []
    for result_node in result.nodes:
        entity_type = entity_types_by_name.get(result_node.type)
        if entity_type is None:
            logs.append(
                f"skipped node {result_node.value!r}: unknown entity type {result_node.type!r}"
            )
            continue
        node, _created = await node_service.create_node(
            db,
            case_id=run.case_id,
            user=triggering_user,
            entity_type_id=entity_type.id,
            value=result_node.value,
            properties=result_node.properties,
            confidence=result_node.confidence,
            created_via=CreatedVia.TRANSFORM,
            created_by_transform_run_id=run.id,
        )
        node_lookup[(entity_type.name, canonicalize(entity_type.name, result_node.value))] = node
        result_node_ids.append(str(node.id))

    result_edge_ids: list[str] = []
    for result_edge in result.edges:
        src_type = entity_types_by_name.get(result_edge.src.type)
        dst_type = entity_types_by_name.get(result_edge.dst.type)
        src_node = (
            node_lookup.get((src_type.name, canonicalize(src_type.name, result_edge.src.value)))
            if src_type
            else None
        )
        dst_node = (
            node_lookup.get((dst_type.name, canonicalize(dst_type.name, result_edge.dst.value)))
            if dst_type
            else None
        )
        if src_node is None or dst_node is None:
            logs.append(f"skipped edge {result_edge.relationship!r}: unresolved endpoint")
            continue
        edge, _created = await edge_service.create_edge(
            db,
            case_id=run.case_id,
            user=triggering_user,
            src_node_id=src_node.id,
            dst_node_id=dst_node.id,
            relationship=result_edge.relationship,
            label=result_edge.label,
            properties=result_edge.properties,
            created_via=CreatedVia.TRANSFORM,
            created_by_transform_run_id=run.id,
        )
        result_edge_ids.append(str(edge.id))

    run.status = TransformRunStatus.SUCCEEDED
    run.result_node_ids = result_node_ids
    run.result_edge_ids = result_edge_ids
    run.logs = [*logs, *result.logs]
    await record_event(
        db,
        case_id=run.case_id,
        actor_type=CreatedVia.TRANSFORM,
        actor_transform_run_id=run.id,
        type="transform_run.completed",
        payload={
            "transform_run_id": str(run.id),
            "result_node_ids": result_node_ids,
            "result_edge_ids": result_edge_ids,
        },
    )
    await db.commit()
    await db.refresh(run)
    return run
