import httpx


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


async def test_group_crud_and_membership(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case = await _create_case(api_client)
    domain_type = await _entity_type_id(api_client, "domain")
    node = (
        await api_client.post(
            f"/api/v1/cases/{case['id']}/nodes",
            json={"entity_type_id": domain_type, "value": "example.com"},
        )
    ).json()

    created = await api_client.post(
        f"/api/v1/cases/{case['id']}/groups", json={"name": "Infra cluster"}
    )
    assert created.status_code == 201
    group = created.json()

    added = await api_client.post(
        f"/api/v1/cases/{case['id']}/groups/{group['id']}/members", json={"node_id": node["id"]}
    )
    assert added.status_code == 204

    members = await api_client.get(f"/api/v1/cases/{case['id']}/groups/{group['id']}/members")
    assert members.json() == [node["id"]]

    removed = await api_client.delete(
        f"/api/v1/cases/{case['id']}/groups/{group['id']}/members/{node['id']}"
    )
    assert removed.status_code == 204

    deleted = await api_client.delete(f"/api/v1/cases/{case['id']}/groups/{group['id']}")
    assert deleted.status_code == 204


async def test_add_member_from_another_case_rejected(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case_1 = await _create_case(api_client, "Case 1")
    case_2 = await _create_case(api_client, "Case 2")
    domain_type = await _entity_type_id(api_client, "domain")
    node = (
        await api_client.post(
            f"/api/v1/cases/{case_2['id']}/nodes",
            json={"entity_type_id": domain_type, "value": "example.com"},
        )
    ).json()
    group = (
        await api_client.post(f"/api/v1/cases/{case_1['id']}/groups", json={"name": "G"})
    ).json()

    response = await api_client.post(
        f"/api/v1/cases/{case_1['id']}/groups/{group['id']}/members", json={"node_id": node["id"]}
    )
    assert response.status_code == 422
