"""Comprehensive role x action authz matrix (PLAN.md Phase 1). Every case-scoped
action has a documented minimum required role (see services/cases.py's
`require_role` call sites). For each action this file checks the boundary:
the role just below the minimum is forbidden, and the minimum role itself
succeeds. That's sufficient to pin the threshold per endpoint without a full
role x action cross product -- `require_role`'s rank comparison is one shared
code path, so proving the boundary holds per endpoint is what actually catches
someone loosening or forgetting a check on a specific route.
"""

from collections.abc import Awaitable, Callable

import httpx

ClientFactory = Callable[[], Awaitable[httpx.AsyncClient]]


async def _register(client: httpx.AsyncClient, email: str) -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": email.split("@")[0], "password": "hunter2pass"},
    )
    assert response.status_code == 201
    return response.json()


async def _create_case(client: httpx.AsyncClient, name: str = "Authz Case") -> dict:
    response = await client.post("/api/v1/cases", json={"name": name})
    assert response.status_code == 201
    return response.json()


async def _entity_type_id(client: httpx.AsyncClient, name: str) -> str:
    listing = (await client.get("/api/v1/entity-types")).json()
    return next(et["id"] for et in listing if et["name"] == name)


async def _create_node(
    client: httpx.AsyncClient, case_id: str, entity_type_id: str, value: str
) -> dict:
    response = await client.post(
        f"/api/v1/cases/{case_id}/nodes", json={"entity_type_id": entity_type_id, "value": value}
    )
    assert response.status_code == 201
    return response.json()


class _Case:
    """A case with owner/editor/viewer/non-member clients and a small graph
    (two nodes, an edge, a note, a waypoint, a group) already in place, built
    fresh per test so mutating actions in one check never affect another."""

    def __init__(
        self, clients: dict[str, httpx.AsyncClient], users: dict[str, dict], ids: dict[str, str]
    ) -> None:
        self.clients = clients
        self.users = users
        self.ids = ids

    def client(self, role: str) -> httpx.AsyncClient:
        return self.clients[role]


async def _build_case(factory: ClientFactory, suffix: str) -> _Case:
    owner = await factory()
    owner_user = await _register(owner, f"owner-{suffix}@example.com")
    case = await _create_case(owner)

    editor = await factory()
    editor_user = await _register(editor, f"editor-{suffix}@example.com")
    add = await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": editor_user["id"], "role": "editor"},
    )
    assert add.status_code == 201

    viewer = await factory()
    viewer_user = await _register(viewer, f"viewer-{suffix}@example.com")
    add = await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": viewer_user["id"], "role": "viewer"},
    )
    assert add.status_code == 201

    nonmember = await factory()
    nonmember_user = await _register(nonmember, f"nonmember-{suffix}@example.com")

    domain_type = await _entity_type_id(owner, "domain")
    ip_type = await _entity_type_id(owner, "ipv4")
    node_a = await _create_node(owner, case["id"], domain_type, f"{suffix}-a.example.com")
    node_b = await _create_node(owner, case["id"], ip_type, f"10.0.{hash(suffix) % 200}.1")
    edge = (
        await owner.post(
            f"/api/v1/cases/{case['id']}/edges",
            json={
                "src_node_id": node_a["id"],
                "dst_node_id": node_b["id"],
                "relationship": "resolves_to",
            },
        )
    ).json()
    note = (
        await owner.post(
            f"/api/v1/cases/{case['id']}/notes", json={"target_type": "case", "body": "seed note"}
        )
    ).json()
    waypoint = (
        await owner.post(
            f"/api/v1/cases/{case['id']}/waypoints",
            json={"name": "seed", "position_x": 0.0, "position_y": 0.0},
        )
    ).json()
    group = (await owner.post(f"/api/v1/cases/{case['id']}/groups", json={"name": "seed"})).json()

    return _Case(
        clients={"owner": owner, "editor": editor, "viewer": viewer, "nonmember": nonmember},
        users={
            "owner": owner_user,
            "editor": editor_user,
            "viewer": viewer_user,
            "nonmember": nonmember_user,
        },
        ids={
            "case": case["id"],
            "domain_type": domain_type,
            "ip_type": ip_type,
            "node_a": node_a["id"],
            "node_b": node_b["id"],
            "edge": edge["id"],
            "note": note["id"],
            "waypoint": waypoint["id"],
            "group": group["id"],
        },
    )


async def _assert_forbidden_then_allowed(
    below: httpx.AsyncClient,
    at_minimum: httpx.AsyncClient,
    request: Callable[[httpx.AsyncClient], Awaitable[httpx.Response]],
) -> httpx.Response:
    forbidden = await request(below)
    assert forbidden.status_code == 403
    allowed = await request(at_minimum)
    assert allowed.status_code < 400
    return allowed


async def test_case_read_requires_viewer(api_client_factory: ClientFactory) -> None:
    c = await _build_case(api_client_factory, "case-read")
    await _assert_forbidden_then_allowed(
        c.client("nonmember"),
        c.client("viewer"),
        lambda cl: cl.get(f"/api/v1/cases/{c.ids['case']}"),
    )
    await _assert_forbidden_then_allowed(
        c.client("nonmember"),
        c.client("viewer"),
        lambda cl: cl.get(f"/api/v1/cases/{c.ids['case']}/members"),
    )


async def test_case_update_requires_editor(api_client_factory: ClientFactory) -> None:
    c = await _build_case(api_client_factory, "case-update")
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.patch(f"/api/v1/cases/{c.ids['case']}", json={"name": "Renamed"}),
    )


async def test_case_delete_and_member_management_requires_owner(
    api_client_factory: ClientFactory,
) -> None:
    c = await _build_case(api_client_factory, "case-owner")
    target = await api_client_factory()
    target_user = await _register(target, "target-case-owner@example.com")

    await _assert_forbidden_then_allowed(
        c.client("editor"),
        c.client("owner"),
        lambda cl: cl.post(
            f"/api/v1/cases/{c.ids['case']}/members",
            json={"user_id": target_user["id"], "role": "viewer"},
        ),
    )
    await _assert_forbidden_then_allowed(
        c.client("editor"),
        c.client("owner"),
        lambda cl: cl.delete(f"/api/v1/cases/{c.ids['case']}/members/{c.users['editor']['id']}"),
    )
    # delete_case last since it tears down the case itself
    forbidden = await c.client("editor").delete(f"/api/v1/cases/{c.ids['case']}")
    assert forbidden.status_code == 403
    allowed = await c.client("owner").delete(f"/api/v1/cases/{c.ids['case']}")
    assert allowed.status_code == 204


async def test_node_read_requires_viewer(api_client_factory: ClientFactory) -> None:
    c = await _build_case(api_client_factory, "node-read")
    await _assert_forbidden_then_allowed(
        c.client("nonmember"),
        c.client("viewer"),
        lambda cl: cl.get(f"/api/v1/cases/{c.ids['case']}/nodes"),
    )
    await _assert_forbidden_then_allowed(
        c.client("nonmember"),
        c.client("viewer"),
        lambda cl: cl.get(f"/api/v1/cases/{c.ids['case']}/nodes/{c.ids['node_a']}"),
    )


async def test_node_writes_require_editor(api_client_factory: ClientFactory) -> None:
    c = await _build_case(api_client_factory, "node-write")
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.post(
            f"/api/v1/cases/{c.ids['case']}/nodes",
            json={"entity_type_id": c.ids["domain_type"], "value": "node-write-new.example.com"},
        ),
    )
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.patch(
            f"/api/v1/cases/{c.ids['case']}/nodes/{c.ids['node_a']}", json={"confidence": 0.5}
        ),
    )
    disposable = await _create_node(
        c.client("owner"), c.ids["case"], c.ids["domain_type"], "node-write-disposable.example.com"
    )
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.delete(f"/api/v1/cases/{c.ids['case']}/nodes/{disposable['id']}"),
    )


async def test_edge_read_requires_viewer(api_client_factory: ClientFactory) -> None:
    c = await _build_case(api_client_factory, "edge-read")
    await _assert_forbidden_then_allowed(
        c.client("nonmember"),
        c.client("viewer"),
        lambda cl: cl.get(f"/api/v1/cases/{c.ids['case']}/edges"),
    )
    await _assert_forbidden_then_allowed(
        c.client("nonmember"),
        c.client("viewer"),
        lambda cl: cl.get(f"/api/v1/cases/{c.ids['case']}/edges/{c.ids['edge']}"),
    )


async def test_edge_writes_require_editor(api_client_factory: ClientFactory) -> None:
    c = await _build_case(api_client_factory, "edge-write")
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.post(
            f"/api/v1/cases/{c.ids['case']}/edges",
            json={
                "src_node_id": c.ids["node_a"],
                "dst_node_id": c.ids["node_b"],
                "relationship": "edge-write-new",
            },
        ),
    )
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.patch(
            f"/api/v1/cases/{c.ids['case']}/edges/{c.ids['edge']}", json={"label": "updated"}
        ),
    )
    disposable = (
        await c.client("owner").post(
            f"/api/v1/cases/{c.ids['case']}/edges",
            json={
                "src_node_id": c.ids["node_a"],
                "dst_node_id": c.ids["node_b"],
                "relationship": "edge-write-disposable",
            },
        )
    ).json()
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.delete(f"/api/v1/cases/{c.ids['case']}/edges/{disposable['id']}"),
    )


async def test_note_read_requires_viewer(api_client_factory: ClientFactory) -> None:
    c = await _build_case(api_client_factory, "note-read")
    await _assert_forbidden_then_allowed(
        c.client("nonmember"),
        c.client("viewer"),
        lambda cl: cl.get(f"/api/v1/cases/{c.ids['case']}/notes"),
    )
    await _assert_forbidden_then_allowed(
        c.client("nonmember"),
        c.client("viewer"),
        lambda cl: cl.get(f"/api/v1/cases/{c.ids['case']}/notes/{c.ids['note']}"),
    )


async def test_note_writes_require_editor(api_client_factory: ClientFactory) -> None:
    c = await _build_case(api_client_factory, "note-write")
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.post(
            f"/api/v1/cases/{c.ids['case']}/notes",
            json={"target_type": "case", "body": "note-write-new"},
        ),
    )
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.patch(
            f"/api/v1/cases/{c.ids['case']}/notes/{c.ids['note']}", json={"body": "updated"}
        ),
    )
    disposable = (
        await c.client("owner").post(
            f"/api/v1/cases/{c.ids['case']}/notes",
            json={"target_type": "case", "body": "note-write-disposable"},
        )
    ).json()
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.delete(f"/api/v1/cases/{c.ids['case']}/notes/{disposable['id']}"),
    )


async def test_waypoint_read_requires_viewer(api_client_factory: ClientFactory) -> None:
    c = await _build_case(api_client_factory, "waypoint-read")
    await _assert_forbidden_then_allowed(
        c.client("nonmember"),
        c.client("viewer"),
        lambda cl: cl.get(f"/api/v1/cases/{c.ids['case']}/waypoints"),
    )
    await _assert_forbidden_then_allowed(
        c.client("nonmember"),
        c.client("viewer"),
        lambda cl: cl.get(f"/api/v1/cases/{c.ids['case']}/waypoints/{c.ids['waypoint']}"),
    )


async def test_waypoint_writes_require_editor(api_client_factory: ClientFactory) -> None:
    c = await _build_case(api_client_factory, "waypoint-write")
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.post(
            f"/api/v1/cases/{c.ids['case']}/waypoints",
            json={"name": "waypoint-write-new", "position_x": 1.0, "position_y": 1.0},
        ),
    )
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.patch(
            f"/api/v1/cases/{c.ids['case']}/waypoints/{c.ids['waypoint']}", json={"zoom": 2.0}
        ),
    )
    disposable = (
        await c.client("owner").post(
            f"/api/v1/cases/{c.ids['case']}/waypoints",
            json={"name": "waypoint-write-disposable", "position_x": 0.0, "position_y": 0.0},
        )
    ).json()
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.delete(f"/api/v1/cases/{c.ids['case']}/waypoints/{disposable['id']}"),
    )


async def test_group_read_requires_viewer(api_client_factory: ClientFactory) -> None:
    c = await _build_case(api_client_factory, "group-read")
    await _assert_forbidden_then_allowed(
        c.client("nonmember"),
        c.client("viewer"),
        lambda cl: cl.get(f"/api/v1/cases/{c.ids['case']}/groups"),
    )
    await _assert_forbidden_then_allowed(
        c.client("nonmember"),
        c.client("viewer"),
        lambda cl: cl.get(f"/api/v1/cases/{c.ids['case']}/groups/{c.ids['group']}"),
    )
    await _assert_forbidden_then_allowed(
        c.client("nonmember"),
        c.client("viewer"),
        lambda cl: cl.get(f"/api/v1/cases/{c.ids['case']}/groups/{c.ids['group']}/members"),
    )


async def test_group_writes_require_editor(api_client_factory: ClientFactory) -> None:
    c = await _build_case(api_client_factory, "group-write")
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.post(
            f"/api/v1/cases/{c.ids['case']}/groups", json={"name": "group-write-new"}
        ),
    )
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.patch(
            f"/api/v1/cases/{c.ids['case']}/groups/{c.ids['group']}", json={"name": "updated"}
        ),
    )

    disposable_node = await _create_node(
        c.client("owner"), c.ids["case"], c.ids["domain_type"], "group-write-member.example.com"
    )
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.post(
            f"/api/v1/cases/{c.ids['case']}/groups/{c.ids['group']}/members",
            json={"node_id": disposable_node["id"]},
        ),
    )
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.delete(
            f"/api/v1/cases/{c.ids['case']}/groups/{c.ids['group']}/members/{disposable_node['id']}"
        ),
    )

    disposable_group = (
        await c.client("owner").post(
            f"/api/v1/cases/{c.ids['case']}/groups", json={"name": "group-write-disposable"}
        )
    ).json()
    await _assert_forbidden_then_allowed(
        c.client("viewer"),
        c.client("editor"),
        lambda cl: cl.delete(f"/api/v1/cases/{c.ids['case']}/groups/{disposable_group['id']}"),
    )
