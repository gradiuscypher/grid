import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.errors import NotFoundError, ValidationError
from grid.db.models import CaseRole, CreatedVia, Edge, GroupMember, Node, User
from grid.events.service import record_event
from grid.services.canonicalize import canonicalize
from grid.services.cases import require_role
from grid.services.entity_types import get_entity_type, validate_properties


async def _find_by_dedup_key(
    db: AsyncSession, *, case_id: uuid.UUID, entity_type_id: uuid.UUID, canonical_value: str
) -> Node | None:
    return await db.scalar(
        select(Node).where(
            Node.case_id == case_id,
            Node.entity_type_id == entity_type_id,
            Node.canonical_value == canonical_value,
        )
    )


async def create_node(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    user: User,
    entity_type_id: uuid.UUID,
    value: str,
    properties: dict[str, Any] | None = None,
    position_x: float = 0.0,
    position_y: float = 0.0,
    confidence: float = 1.0,
) -> tuple[Node, bool]:
    """Returns `(node, created)`. Dedup is structural (ARCHITECTURE §3): a repeat
    create with the same (case_id, entity_type, canonical_value) returns the
    existing node rather than erroring."""
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    entity_type = await get_entity_type(db, entity_type_id=entity_type_id)
    properties = properties or {}
    validate_properties(entity_type, properties)
    try:
        canonical_value = canonicalize(entity_type.name, value)
    except ValueError as exc:
        raise ValidationError(f"invalid value for {entity_type.name!r}: {exc}") from exc

    existing = await _find_by_dedup_key(
        db, case_id=case_id, entity_type_id=entity_type_id, canonical_value=canonical_value
    )
    if existing is not None:
        return existing, False

    node = Node(
        case_id=case_id,
        entity_type_id=entity_type_id,
        value=value,
        canonical_value=canonical_value,
        properties=properties,
        position_x=position_x,
        position_y=position_y,
        confidence=confidence,
        created_via=CreatedVia.USER,
        created_by_user_id=user.id,
    )
    db.add(node)
    try:
        await db.flush()
    except IntegrityError:
        # Lost a create race to a concurrent request with the same dedup key.
        await db.rollback()
        existing = await _find_by_dedup_key(
            db, case_id=case_id, entity_type_id=entity_type_id, canonical_value=canonical_value
        )
        if existing is not None:
            return existing, False
        raise

    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="node.created",
        payload={
            "node_id": str(node.id),
            "entity_type": entity_type.name,
            "value": value,
            "canonical_value": canonical_value,
        },
    )
    await db.commit()
    await db.refresh(node)
    return node, True


async def get_node(db: AsyncSession, *, case_id: uuid.UUID, node_id: uuid.UUID, user: User) -> Node:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    node = await db.get(Node, node_id)
    if node is None or node.case_id != case_id:
        raise NotFoundError("node not found")
    return node


async def list_nodes(db: AsyncSession, *, case_id: uuid.UUID, user: User) -> list[Node]:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    result = await db.scalars(select(Node).where(Node.case_id == case_id))
    return list(result)


async def update_node(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    node_id: uuid.UUID,
    user: User,
    properties: dict[str, Any] | None = None,
    position_x: float | None = None,
    position_y: float | None = None,
    confidence: float | None = None,
) -> Node:
    """Identity fields (`entity_type`, `value`/`canonical_value`) are immutable
    after creation — changing them would silently break dedup semantics for
    anything that already linked to this node."""
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    node = await get_node(db, case_id=case_id, node_id=node_id, user=user)
    if properties is not None:
        entity_type = await get_entity_type(db, entity_type_id=node.entity_type_id)
        validate_properties(entity_type, properties)
        node.properties = properties
    if position_x is not None:
        node.position_x = position_x
    if position_y is not None:
        node.position_y = position_y
    if confidence is not None:
        node.confidence = confidence
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="node.updated",
        payload={"node_id": str(node.id)},
    )
    await db.commit()
    await db.refresh(node)
    return node


async def delete_node(
    db: AsyncSession, *, case_id: uuid.UUID, node_id: uuid.UUID, user: User
) -> None:
    """Deleting a node is a structural graph edit: its edges and group
    memberships are cascaded rather than left to violate a FK constraint."""
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    node = await get_node(db, case_id=case_id, node_id=node_id, user=user)

    edge_ids = list(
        await db.scalars(
            select(Edge.id).where(
                Edge.case_id == case_id,
                (Edge.src_node_id == node_id) | (Edge.dst_node_id == node_id),
            )
        )
    )
    if edge_ids:
        await db.execute(delete(Edge).where(Edge.id.in_(edge_ids)))
    await db.execute(delete(GroupMember).where(GroupMember.node_id == node_id))

    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="node.deleted",
        payload={"node_id": str(node.id), "cascaded_edge_ids": [str(i) for i in edge_ids]},
    )
    await db.delete(node)
    await db.commit()
