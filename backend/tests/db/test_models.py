import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from grid.db.models import Case, CreatedVia, EntityType, Node, User


async def _make_user(db_session: AsyncSession) -> User:
    user = User(email="a@example.com", display_name="A", password_hash="x")
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_case(db_session: AsyncSession, user: User) -> Case:
    case = Case(name="Case A", created_by_user_id=user.id)
    db_session.add(case)
    await db_session.flush()
    return case


async def _make_entity_type(db_session: AsyncSession) -> EntityType:
    et = EntityType(name="domain", display_name="Domain", is_builtin=True, json_schema={})
    db_session.add(et)
    await db_session.flush()
    return et


async def test_node_dedup_unique_constraint(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    case = await _make_case(db_session, user)
    et = await _make_entity_type(db_session)

    node = Node(
        case_id=case.id,
        entity_type_id=et.id,
        value="Example.com",
        canonical_value="example.com",
        created_via=CreatedVia.USER,
        created_by_user_id=user.id,
    )
    db_session.add(node)
    await db_session.flush()

    dup = Node(
        case_id=case.id,
        entity_type_id=et.id,
        value="EXAMPLE.COM",
        canonical_value="example.com",
        created_via=CreatedVia.USER,
        created_by_user_id=user.id,
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        await db_session.flush()
