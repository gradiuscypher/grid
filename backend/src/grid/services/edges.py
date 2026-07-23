import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.errors import NotFoundError, ValidationError
from grid.db.models import CaseRole, CreatedVia, Edge, Node, User
from grid.events.service import record_event
from grid.services.cases import require_role


async def _find_by_dedup_key(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    src_node_id: uuid.UUID,
    dst_node_id: uuid.UUID,
    relationship: str,
) -> Edge | None:
    return await db.scalar(
        select(Edge).where(
            Edge.case_id == case_id,
            Edge.src_node_id == src_node_id,
            Edge.dst_node_id == dst_node_id,
            Edge.relationship == relationship,
        )
    )


async def _require_node_in_case(
    db: AsyncSession, *, case_id: uuid.UUID, node_id: uuid.UUID
) -> None:
    node = await db.get(Node, node_id)
    if node is None or node.case_id != case_id:
        raise ValidationError(f"node {node_id} does not exist in this case")


async def create_edge(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    user: User,
    src_node_id: uuid.UUID,
    dst_node_id: uuid.UUID,
    relationship: str,
    label: str | None = None,
    properties: dict[str, Any] | None = None,
) -> tuple[Edge, bool]:
    """Returns `(edge, created)`. Same structural-dedup contract as nodes."""
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    await _require_node_in_case(db, case_id=case_id, node_id=src_node_id)
    await _require_node_in_case(db, case_id=case_id, node_id=dst_node_id)

    existing = await _find_by_dedup_key(
        db,
        case_id=case_id,
        src_node_id=src_node_id,
        dst_node_id=dst_node_id,
        relationship=relationship,
    )
    if existing is not None:
        return existing, False

    edge = Edge(
        case_id=case_id,
        src_node_id=src_node_id,
        dst_node_id=dst_node_id,
        relationship=relationship,
        label=label,
        properties=properties or {},
        created_via=CreatedVia.USER,
        created_by_user_id=user.id,
    )
    db.add(edge)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        existing = await _find_by_dedup_key(
            db,
            case_id=case_id,
            src_node_id=src_node_id,
            dst_node_id=dst_node_id,
            relationship=relationship,
        )
        if existing is not None:
            return existing, False
        raise

    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="edge.created",
        payload={
            "edge_id": str(edge.id),
            "src_node_id": str(src_node_id),
            "dst_node_id": str(dst_node_id),
            "relationship": relationship,
        },
    )
    await db.commit()
    await db.refresh(edge)
    return edge, True


async def get_edge(db: AsyncSession, *, case_id: uuid.UUID, edge_id: uuid.UUID, user: User) -> Edge:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    edge = await db.get(Edge, edge_id)
    if edge is None or edge.case_id != case_id:
        raise NotFoundError("edge not found")
    return edge


async def list_edges(db: AsyncSession, *, case_id: uuid.UUID, user: User) -> list[Edge]:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    result = await db.scalars(select(Edge).where(Edge.case_id == case_id))
    return list(result)


async def update_edge(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    edge_id: uuid.UUID,
    user: User,
    label: str | None = None,
    properties: dict[str, Any] | None = None,
) -> Edge:
    """`src`/`dst`/`relationship` are immutable after creation for the same
    dedup-identity reason as node identity fields."""
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    edge = await get_edge(db, case_id=case_id, edge_id=edge_id, user=user)
    if label is not None:
        edge.label = label
    if properties is not None:
        edge.properties = properties
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="edge.updated",
        payload={"edge_id": str(edge.id)},
    )
    await db.commit()
    await db.refresh(edge)
    return edge


async def delete_edge(
    db: AsyncSession, *, case_id: uuid.UUID, edge_id: uuid.UUID, user: User
) -> None:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    edge = await get_edge(db, case_id=case_id, edge_id=edge_id, user=user)
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="edge.deleted",
        payload={"edge_id": str(edge.id)},
    )
    await db.delete(edge)
    await db.commit()
