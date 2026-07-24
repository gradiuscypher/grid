import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.errors import ForbiddenError, ValidationError
from grid.db.models import (
    CaseRole,
    CreatedVia,
    EntityType,
    Node,
    Transform,
    TransformKind,
    TransformRunStatus,
    User,
)
from grid.services import cases as case_service
from grid.services import nodes as node_service
from grid.services import transforms as transform_service
from grid.transforms.spec import EntityRef, RunResult, RunResultEdge, RunResultNode


async def _make_user(db_session: AsyncSession, email: str = "a@example.com") -> User:
    user = User(email=email, display_name=email.split("@")[0], password_hash="x")
    db_session.add(user)
    await db_session.flush()
    return user


async def _entity_type(db_session: AsyncSession, name: str) -> EntityType:
    et = await db_session.scalar(select(EntityType).where(EntityType.name == name))
    assert et is not None
    return et


async def _transform(db_session: AsyncSession, slug: str) -> Transform:
    t = await db_session.scalar(select(Transform).where(Transform.slug == slug))
    assert t is not None
    return t


async def test_sync_builtin_transforms_registers_dns_and_crtsh(db_session: AsyncSession) -> None:
    slugs = {t.slug for t in (await db_session.scalars(select(Transform))).all()}
    assert {"dns_forward", "dns_reverse", "crtsh_subdomains"} <= slugs
    dns_forward = await _transform(db_session, "dns_forward")
    assert dns_forward.kind == TransformKind.BUILTIN
    assert dns_forward.input_types == ["domain", "hostname"]
    assert dns_forward.output_types == ["ipv4", "ipv6"]


async def test_start_transform_run_rejects_wrong_input_type(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    case = await case_service.create_case(db_session, user=user, name="Case A")
    ipv4 = await _entity_type(db_session, "ipv4")
    node, _ = await node_service.create_node(
        db_session, case_id=case.id, user=user, entity_type_id=ipv4.id, value="1.2.3.4"
    )
    crtsh = await _transform(db_session, "crtsh_subdomains")  # takes "domain", not "ipv4"

    with pytest.raises(ValidationError):
        await transform_service.start_transform_run(
            db_session,
            case_id=case.id,
            transform_id=crtsh.id,
            input_node_ids=[node.id],
            params=None,
            user=user,
        )


async def test_start_transform_run_requires_editor_role(db_session: AsyncSession) -> None:
    owner = await _make_user(db_session, "owner@example.com")
    viewer = await _make_user(db_session, "viewer@example.com")
    case = await case_service.create_case(db_session, user=owner, name="Case A")
    await case_service.add_member(
        db_session, case_id=case.id, actor=owner, target_user_id=viewer.id, role=CaseRole.VIEWER
    )
    domain = await _entity_type(db_session, "domain")
    node, _ = await node_service.create_node(
        db_session, case_id=case.id, user=owner, entity_type_id=domain.id, value="example.com"
    )
    dns_forward = await _transform(db_session, "dns_forward")

    with pytest.raises(ForbiddenError):
        await transform_service.start_transform_run(
            db_session,
            case_id=case.id,
            transform_id=dns_forward.id,
            input_node_ids=[node.id],
            params=None,
            user=viewer,
        )


async def test_start_transform_run_creates_pending_run(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    case = await case_service.create_case(db_session, user=user, name="Case A")
    domain = await _entity_type(db_session, "domain")
    node, _ = await node_service.create_node(
        db_session, case_id=case.id, user=user, entity_type_id=domain.id, value="example.com"
    )
    dns_forward = await _transform(db_session, "dns_forward")

    run = await transform_service.start_transform_run(
        db_session,
        case_id=case.id,
        transform_id=dns_forward.id,
        input_node_ids=[node.id],
        params=None,
        user=user,
    )
    assert run.status == TransformRunStatus.PENDING
    assert run.input_node_ids == [str(node.id)]
    assert run.triggered_by_user_id == user.id


async def test_merge_transform_results_creates_nodes_edges_with_transform_provenance(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session)
    case = await case_service.create_case(db_session, user=user, name="Case A")
    domain = await _entity_type(db_session, "domain")
    node, _ = await node_service.create_node(
        db_session, case_id=case.id, user=user, entity_type_id=domain.id, value="example.com"
    )
    dns_forward = await _transform(db_session, "dns_forward")
    run = await transform_service.start_transform_run(
        db_session,
        case_id=case.id,
        transform_id=dns_forward.id,
        input_node_ids=[node.id],
        params=None,
        user=user,
    )

    result = RunResult(
        nodes=[RunResultNode(type="ipv4", value="93.184.216.34")],
        edges=[
            RunResultEdge(
                src=EntityRef(type="domain", value="example.com"),
                dst=EntityRef(type="ipv4", value="93.184.216.34"),
                relationship="resolves_to",
            )
        ],
        logs=["1 A record found"],
    )

    updated = await transform_service.merge_transform_results(
        db_session, run_id=run.id, result=result
    )

    assert updated.status == TransformRunStatus.SUCCEEDED
    assert len(updated.result_node_ids) == 1
    assert len(updated.result_edge_ids) == 1
    assert "1 A record found" in updated.logs

    new_node = await db_session.get(Node, uuid.UUID(updated.result_node_ids[0]))
    assert new_node is not None
    assert new_node.created_via == CreatedVia.TRANSFORM
    assert new_node.created_by_transform_run_id == run.id
    assert new_node.created_by_user_id is None


async def test_merge_transform_results_dedups_against_existing_node(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session)
    case = await case_service.create_case(db_session, user=user, name="Case A")
    domain = await _entity_type(db_session, "domain")
    ipv4 = await _entity_type(db_session, "ipv4")
    src_node, _ = await node_service.create_node(
        db_session, case_id=case.id, user=user, entity_type_id=domain.id, value="example.com"
    )
    existing_ip, _ = await node_service.create_node(
        db_session, case_id=case.id, user=user, entity_type_id=ipv4.id, value="93.184.216.34"
    )
    dns_forward = await _transform(db_session, "dns_forward")
    run = await transform_service.start_transform_run(
        db_session,
        case_id=case.id,
        transform_id=dns_forward.id,
        input_node_ids=[src_node.id],
        params=None,
        user=user,
    )

    result = RunResult(
        nodes=[RunResultNode(type="ipv4", value="93.184.216.34")],
        edges=[
            RunResultEdge(
                src=EntityRef(type="domain", value="example.com"),
                dst=EntityRef(type="ipv4", value="93.184.216.34"),
                relationship="resolves_to",
            )
        ],
    )
    updated = await transform_service.merge_transform_results(
        db_session, run_id=run.id, result=result
    )

    assert updated.result_node_ids == [str(existing_ip.id)]
    refreshed = await db_session.get(Node, existing_ip.id)
    assert refreshed is not None
    assert refreshed.created_via == CreatedVia.USER  # dedup: pre-existing provenance untouched


async def test_merge_transform_results_skips_edge_with_unresolvable_endpoint(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session)
    case = await case_service.create_case(db_session, user=user, name="Case A")
    domain = await _entity_type(db_session, "domain")
    node, _ = await node_service.create_node(
        db_session, case_id=case.id, user=user, entity_type_id=domain.id, value="example.com"
    )
    dns_forward = await _transform(db_session, "dns_forward")
    run = await transform_service.start_transform_run(
        db_session,
        case_id=case.id,
        transform_id=dns_forward.id,
        input_node_ids=[node.id],
        params=None,
        user=user,
    )

    # Edge references a src the transform never returned as a node and isn't an
    # input — nothing to resolve it against, so it's dropped and logged rather
    # than crashing the whole merge.
    result = RunResult(
        edges=[
            RunResultEdge(
                src=EntityRef(type="domain", value="never-created.example.com"),
                dst=EntityRef(type="domain", value="example.com"),
                relationship="resolves_to",
            )
        ]
    )
    updated = await transform_service.merge_transform_results(
        db_session, run_id=run.id, result=result
    )

    assert updated.result_edge_ids == []
    assert any("unresolved endpoint" in log for log in updated.logs)
