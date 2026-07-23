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


async def test_create_node_and_dedup_on_repeat(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case = await _create_case(api_client)
    domain_type = await _entity_type_id(api_client, "domain")

    first = await api_client.post(
        f"/api/v1/cases/{case['id']}/nodes",
        json={"entity_type_id": domain_type, "value": "Example.com"},
    )
    assert first.status_code == 201
    node = first.json()
    assert node["canonical_value"] == "example.com"

    repeat = await api_client.post(
        f"/api/v1/cases/{case['id']}/nodes",
        json={"entity_type_id": domain_type, "value": "EXAMPLE.COM"},
    )
    assert repeat.status_code == 200
    assert repeat.json()["id"] == node["id"]

    listing = await api_client.get(f"/api/v1/cases/{case['id']}/nodes")
    assert len(listing.json()) == 1


async def test_node_properties_validated_against_entity_type_schema(
    api_client: httpx.AsyncClient,
) -> None:
    await _register(api_client)
    case = await _create_case(api_client)
    custom = await api_client.post(
        "/api/v1/entity-types",
        json={
            "name": "crypto_wallet",
            "display_name": "Crypto Wallet",
            "json_schema": {
                "type": "object",
                "properties": {"chain": {"type": "string"}},
                "required": ["chain"],
            },
        },
    )
    entity_type_id = custom.json()["id"]

    bad = await api_client.post(
        f"/api/v1/cases/{case['id']}/nodes",
        json={"entity_type_id": entity_type_id, "value": "0xabc", "properties": {}},
    )
    assert bad.status_code == 422

    good = await api_client.post(
        f"/api/v1/cases/{case['id']}/nodes",
        json={"entity_type_id": entity_type_id, "value": "0xabc", "properties": {"chain": "eth"}},
    )
    assert good.status_code == 201


async def test_invalid_ipv4_value_rejected(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case = await _create_case(api_client)
    ipv4_type = await _entity_type_id(api_client, "ipv4")

    response = await api_client.post(
        f"/api/v1/cases/{case['id']}/nodes",
        json={"entity_type_id": ipv4_type, "value": "not-an-ip"},
    )
    assert response.status_code == 422


async def test_viewer_cannot_create_node(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    case = await _create_case(owner)
    domain_type = await _entity_type_id(owner, "domain")

    viewer = await api_client_factory()
    viewer_user = await _register(viewer, "viewer@example.com")
    await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": viewer_user["id"], "role": "viewer"},
    )

    response = await viewer.post(
        f"/api/v1/cases/{case['id']}/nodes",
        json={"entity_type_id": domain_type, "value": "example.com"},
    )
    assert response.status_code == 403


async def test_update_node_cannot_change_identity_fields(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case = await _create_case(api_client)
    domain_type = await _entity_type_id(api_client, "domain")
    node = (
        await api_client.post(
            f"/api/v1/cases/{case['id']}/nodes",
            json={"entity_type_id": domain_type, "value": "example.com"},
        )
    ).json()

    updated = await api_client.patch(
        f"/api/v1/cases/{case['id']}/nodes/{node['id']}",
        json={"position_x": 10.0, "confidence": 0.5},
    )
    assert updated.status_code == 200
    assert updated.json()["position_x"] == 10.0
    assert updated.json()["confidence"] == 0.5
    assert updated.json()["value"] == "example.com"


async def test_delete_node_cascades_edges(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case = await _create_case(api_client)
    domain_type = await _entity_type_id(api_client, "domain")
    ip_type = await _entity_type_id(api_client, "ipv4")

    a = (
        await api_client.post(
            f"/api/v1/cases/{case['id']}/nodes",
            json={"entity_type_id": domain_type, "value": "example.com"},
        )
    ).json()
    b = (
        await api_client.post(
            f"/api/v1/cases/{case['id']}/nodes",
            json={"entity_type_id": ip_type, "value": "1.2.3.4"},
        )
    ).json()
    edge = (
        await api_client.post(
            f"/api/v1/cases/{case['id']}/edges",
            json={"src_node_id": a["id"], "dst_node_id": b["id"], "relationship": "resolves_to"},
        )
    ).json()

    deleted = await api_client.delete(f"/api/v1/cases/{case['id']}/nodes/{a['id']}")
    assert deleted.status_code == 204

    get_edge = await api_client.get(f"/api/v1/cases/{case['id']}/edges/{edge['id']}")
    assert get_edge.status_code == 404
