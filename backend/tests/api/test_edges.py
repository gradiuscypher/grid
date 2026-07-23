from collections.abc import Awaitable, Callable

import httpx

ClientFactory = Callable[[], Awaitable[httpx.AsyncClient]]


async def _register(client: httpx.AsyncClient, email: str = "owner@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": email.split("@")[0], "password": "hunter2pass"},
    )
    assert response.status_code == 201
    return response.json()


async def _create_case(client: httpx.AsyncClient, name: str = "Case A") -> dict:
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


async def test_create_edge_and_dedup_on_repeat(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case = await _create_case(api_client)
    domain_type = await _entity_type_id(api_client, "domain")
    ip_type = await _entity_type_id(api_client, "ipv4")
    a = await _create_node(api_client, case["id"], domain_type, "example.com")
    b = await _create_node(api_client, case["id"], ip_type, "1.2.3.4")

    first = await api_client.post(
        f"/api/v1/cases/{case['id']}/edges",
        json={"src_node_id": a["id"], "dst_node_id": b["id"], "relationship": "resolves_to"},
    )
    assert first.status_code == 201
    edge = first.json()

    repeat = await api_client.post(
        f"/api/v1/cases/{case['id']}/edges",
        json={"src_node_id": a["id"], "dst_node_id": b["id"], "relationship": "resolves_to"},
    )
    assert repeat.status_code == 200
    assert repeat.json()["id"] == edge["id"]


async def test_edge_rejects_node_from_another_case(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case_1 = await _create_case(api_client, "Case 1")
    case_2 = await _create_case(api_client, "Case 2")
    domain_type = await _entity_type_id(api_client, "domain")
    a = await _create_node(api_client, case_1["id"], domain_type, "example.com")
    b = await _create_node(api_client, case_2["id"], domain_type, "other.com")

    response = await api_client.post(
        f"/api/v1/cases/{case_1['id']}/edges",
        json={"src_node_id": a["id"], "dst_node_id": b["id"], "relationship": "resolves_to"},
    )
    assert response.status_code == 422


async def test_viewer_cannot_create_edge(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    case = await _create_case(owner)
    domain_type = await _entity_type_id(owner, "domain")
    a = await _create_node(owner, case["id"], domain_type, "example.com")
    b = await _create_node(owner, case["id"], domain_type, "other.com")

    viewer = await api_client_factory()
    viewer_user = await _register(viewer, "viewer@example.com")
    await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": viewer_user["id"], "role": "viewer"},
    )

    response = await viewer.post(
        f"/api/v1/cases/{case['id']}/edges",
        json={"src_node_id": a["id"], "dst_node_id": b["id"], "relationship": "resolves_to"},
    )
    assert response.status_code == 403


async def test_delete_edge(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case = await _create_case(api_client)
    domain_type = await _entity_type_id(api_client, "domain")
    a = await _create_node(api_client, case["id"], domain_type, "example.com")
    b = await _create_node(api_client, case["id"], domain_type, "other.com")
    edge = (
        await api_client.post(
            f"/api/v1/cases/{case['id']}/edges",
            json={"src_node_id": a["id"], "dst_node_id": b["id"], "relationship": "links_to"},
        )
    ).json()

    deleted = await api_client.delete(f"/api/v1/cases/{case['id']}/edges/{edge['id']}")
    assert deleted.status_code == 204
    assert (
        await api_client.get(f"/api/v1/cases/{case['id']}/edges/{edge['id']}")
    ).status_code == 404
