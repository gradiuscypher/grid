import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.errors import ForbiddenError, NotFoundError
from grid.db.models import Case, CaseMember, CaseRole, User
from grid.db.models.cases import ROLE_RANK


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
    await db.commit()
    await db.refresh(case)
    return case


async def get_case(db: AsyncSession, *, case_id: uuid.UUID, user: User) -> Case:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    case = await db.get(Case, case_id)
    if case is None:
        raise NotFoundError("case not found")
    return case


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


async def add_member(
    db: AsyncSession, *, case_id: uuid.UUID, actor: User, target_user_id: uuid.UUID, role: CaseRole
) -> CaseMember:
    await require_role(db, case_id=case_id, user_id=actor.id, minimum=CaseRole.OWNER)
    existing = await db.get(CaseMember, {"case_id": case_id, "user_id": target_user_id})
    if existing is not None:
        existing.role = role
        await db.commit()
        return existing
    member = CaseMember(case_id=case_id, user_id=target_user_id, role=role)
    db.add(member)
    await db.commit()
    return member


async def remove_member(
    db: AsyncSession, *, case_id: uuid.UUID, actor: User, target_user_id: uuid.UUID
) -> None:
    await require_role(db, case_id=case_id, user_id=actor.id, minimum=CaseRole.OWNER)
    member = await db.get(CaseMember, {"case_id": case_id, "user_id": target_user_id})
    if member is None:
        raise NotFoundError("member not found")
    if member.role == CaseRole.OWNER:
        owners = await db.scalars(
            select(CaseMember).where(
                CaseMember.case_id == case_id, CaseMember.role == CaseRole.OWNER
            )
        )
        if len(list(owners)) <= 1:
            raise ForbiddenError("cannot remove the last owner")
    await db.delete(member)
    await db.commit()
