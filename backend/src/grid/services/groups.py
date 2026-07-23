import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.errors import NotFoundError, ValidationError
from grid.db.models import CaseRole, CreatedVia, Group, GroupMember, Node, User
from grid.events.service import record_event
from grid.services.cases import require_role


async def create_group(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    user: User,
    name: str,
    context_note: str | None = None,
    color: str | None = None,
) -> Group:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    group = Group(
        case_id=case_id,
        name=name,
        context_note=context_note,
        color=color,
        created_by_user_id=user.id,
    )
    db.add(group)
    await db.flush()
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="group.created",
        payload={"group_id": str(group.id), "name": name},
    )
    await db.commit()
    await db.refresh(group)
    return group


async def get_group(
    db: AsyncSession, *, case_id: uuid.UUID, group_id: uuid.UUID, user: User
) -> Group:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    group = await db.get(Group, group_id)
    if group is None or group.case_id != case_id:
        raise NotFoundError("group not found")
    return group


async def list_groups(db: AsyncSession, *, case_id: uuid.UUID, user: User) -> list[Group]:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    result = await db.scalars(select(Group).where(Group.case_id == case_id))
    return list(result)


async def update_group(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    group_id: uuid.UUID,
    user: User,
    name: str | None = None,
    context_note: str | None = None,
    color: str | None = None,
) -> Group:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    group = await get_group(db, case_id=case_id, group_id=group_id, user=user)
    if name is not None:
        group.name = name
    if context_note is not None:
        group.context_note = context_note
    if color is not None:
        group.color = color
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="group.updated",
        payload={"group_id": str(group.id)},
    )
    await db.commit()
    await db.refresh(group)
    return group


async def delete_group(
    db: AsyncSession, *, case_id: uuid.UUID, group_id: uuid.UUID, user: User
) -> None:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    group = await get_group(db, case_id=case_id, group_id=group_id, user=user)
    await db.execute(delete(GroupMember).where(GroupMember.group_id == group_id))
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="group.deleted",
        payload={"group_id": str(group.id)},
    )
    await db.delete(group)
    await db.commit()


async def list_group_members(
    db: AsyncSession, *, case_id: uuid.UUID, group_id: uuid.UUID, user: User
) -> list[uuid.UUID]:
    await get_group(db, case_id=case_id, group_id=group_id, user=user)
    result = await db.scalars(select(GroupMember.node_id).where(GroupMember.group_id == group_id))
    return list(result)


async def add_group_member(
    db: AsyncSession, *, case_id: uuid.UUID, group_id: uuid.UUID, user: User, node_id: uuid.UUID
) -> None:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    await get_group(db, case_id=case_id, group_id=group_id, user=user)
    node = await db.get(Node, node_id)
    if node is None or node.case_id != case_id:
        raise ValidationError(f"node {node_id} does not exist in this case")
    existing = await db.get(GroupMember, {"group_id": group_id, "node_id": node_id})
    if existing is not None:
        return
    db.add(GroupMember(group_id=group_id, node_id=node_id))
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="group.member_added",
        payload={"group_id": str(group_id), "node_id": str(node_id)},
    )
    await db.commit()


async def remove_group_member(
    db: AsyncSession, *, case_id: uuid.UUID, group_id: uuid.UUID, user: User, node_id: uuid.UUID
) -> None:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    await get_group(db, case_id=case_id, group_id=group_id, user=user)
    member = await db.get(GroupMember, {"group_id": group_id, "node_id": node_id})
    if member is None:
        raise NotFoundError("group member not found")
    await db.delete(member)
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="group.member_removed",
        payload={"group_id": str(group_id), "node_id": str(node_id)},
    )
    await db.commit()
