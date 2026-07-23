import uuid

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.errors import ForbiddenError, NotFoundError
from grid.db.models import (
    Case,
    CaseMember,
    CaseRole,
    CreatedVia,
    Edge,
    Event,
    Group,
    GroupMember,
    Node,
    Note,
    User,
    Waypoint,
)
from grid.db.models.cases import ROLE_RANK
from grid.events.service import record_event


async def get_role(db: AsyncSession, *, case_id: uuid.UUID, user_id: uuid.UUID) -> CaseRole | None:
    member = await db.get(CaseMember, {"case_id": case_id, "user_id": user_id})
    return member.role if member else None


async def require_role(
    db: AsyncSession, *, case_id: uuid.UUID, user_id: uuid.UUID, minimum: CaseRole
) -> CaseRole:
    role = await get_role(db, case_id=case_id, user_id=user_id)
    if role is None or ROLE_RANK[role] < ROLE_RANK[minimum]:
        raise ForbiddenError(f"requires at least {minimum.value} role on this case")
    return role


async def create_case(
    db: AsyncSession, *, user: User, name: str, description: str | None = None
) -> Case:
    case = Case(name=name, description=description, created_by_user_id=user.id)
    db.add(case)
    await db.flush()
    db.add(CaseMember(case_id=case.id, user_id=user.id, role=CaseRole.OWNER))
    await record_event(
        db,
        case_id=case.id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="case.created",
        payload={"case_id": str(case.id), "name": name},
    )
    await db.commit()
    await db.refresh(case)
    return case


async def get_case(db: AsyncSession, *, case_id: uuid.UUID, user: User) -> Case:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    case = await db.get(Case, case_id)
    if case is None:
        raise NotFoundError("case not found")
    return case


async def update_case(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    user: User,
    name: str | None = None,
    description: str | None = None,
) -> Case:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    case = await get_case(db, case_id=case_id, user=user)
    if name is not None:
        case.name = name
    if description is not None:
        case.description = description
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="case.updated",
        payload={"case_id": str(case_id)},
    )
    await db.commit()
    await db.refresh(case)
    return case


async def delete_case(db: AsyncSession, *, case_id: uuid.UUID, user: User) -> None:
    """Owner-only. Children have no DB-level cascade (service layer is the only
    writer, per ARCHITECTURE §2), so every dependent table is cleared manually
    in FK-safe order before the case row itself goes."""
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.OWNER)
    case = await get_case(db, case_id=case_id, user=user)

    await db.execute(
        delete(GroupMember).where(
            GroupMember.group_id.in_(select(Group.id).where(Group.case_id == case_id))
        )
    )
    await db.execute(delete(Note).where(Note.case_id == case_id))
    await db.execute(delete(Waypoint).where(Waypoint.case_id == case_id))
    await db.execute(delete(Group).where(Group.case_id == case_id))
    await db.execute(delete(Edge).where(Edge.case_id == case_id))
    await db.execute(delete(Node).where(Node.case_id == case_id))
    await db.execute(delete(Event).where(Event.case_id == case_id))
    await db.execute(delete(CaseMember).where(CaseMember.case_id == case_id))
    await db.delete(case)
    await db.commit()


async def list_my_cases(db: AsyncSession, *, user: User) -> list[Case]:
    result = await db.scalars(
        select(Case)
        .join(CaseMember, CaseMember.case_id == Case.id)
        .where(CaseMember.user_id == user.id)
    )
    return list(result)


async def list_members(db: AsyncSession, *, case_id: uuid.UUID, user: User) -> list[CaseMember]:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    result = await db.scalars(select(CaseMember).where(CaseMember.case_id == case_id))
    return list(result)


async def _count_owners(db: AsyncSession, *, case_id: uuid.UUID) -> int:
    owners = await db.scalars(
        select(CaseMember).where(CaseMember.case_id == case_id, CaseMember.role == CaseRole.OWNER)
    )
    return len(list(owners))


async def add_member(
    db: AsyncSession, *, case_id: uuid.UUID, actor: User, target_user_id: uuid.UUID, role: CaseRole
) -> CaseMember:
    await require_role(db, case_id=case_id, user_id=actor.id, minimum=CaseRole.OWNER)
    existing = await db.get(CaseMember, {"case_id": case_id, "user_id": target_user_id})
    if existing is not None:
        if (
            existing.role == CaseRole.OWNER
            and role != CaseRole.OWNER
            and await _count_owners(db, case_id=case_id) <= 1
        ):
            raise ForbiddenError("cannot demote the last owner")
        existing.role = role
        await record_event(
            db,
            case_id=case_id,
            actor_type=CreatedVia.USER,
            actor_user_id=actor.id,
            type="case.member_role_changed",
            payload={"user_id": str(target_user_id), "role": role.value},
        )
        await db.commit()
        return existing
    member = CaseMember(case_id=case_id, user_id=target_user_id, role=role)
    db.add(member)
    try:
        await record_event(
            db,
            case_id=case_id,
            actor_type=CreatedVia.USER,
            actor_user_id=actor.id,
            type="case.member_added",
            payload={"user_id": str(target_user_id), "role": role.value},
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise NotFoundError(f"user {target_user_id} not found") from exc
    return member


async def remove_member(
    db: AsyncSession, *, case_id: uuid.UUID, actor: User, target_user_id: uuid.UUID
) -> None:
    await require_role(db, case_id=case_id, user_id=actor.id, minimum=CaseRole.OWNER)
    member = await db.get(CaseMember, {"case_id": case_id, "user_id": target_user_id})
    if member is None:
        raise NotFoundError("member not found")
    if member.role == CaseRole.OWNER and await _count_owners(db, case_id=case_id) <= 1:
        raise ForbiddenError("cannot remove the last owner")
    await db.delete(member)
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=actor.id,
        type="case.member_removed",
        payload={"user_id": str(target_user_id)},
    )
    await db.commit()
