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


async def test_case_level_note(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case = await _create_case(api_client)

    created = await api_client.post(
        f"/api/v1/cases/{case['id']}/notes",
        json={"target_type": "case", "body": "initial findings"},
    )
    assert created.status_code == 201
    note = created.json()
    assert note["target_id"] is None

    updated = await api_client.patch(
        f"/api/v1/cases/{case['id']}/notes/{note['id']}", json={"body": "revised findings"}
    )
    assert updated.status_code == 200
    assert updated.json()["body"] == "revised findings"


async def test_note_requires_target_id_for_node(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case = await _create_case(api_client)

    response = await api_client.post(
        f"/api/v1/cases/{case['id']}/notes", json={"target_type": "node", "body": "orphan note"}
    )
    assert response.status_code == 422


async def test_note_on_node_from_another_case_rejected(api_client: httpx.AsyncClient) -> None:
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

    response = await api_client.post(
        f"/api/v1/cases/{case_1['id']}/notes",
        json={"target_type": "node", "target_id": node["id"], "body": "cross-case note"},
    )
    assert response.status_code == 422


async def test_delete_note(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case = await _create_case(api_client)
    note = (
        await api_client.post(
            f"/api/v1/cases/{case['id']}/notes", json={"target_type": "case", "body": "temp"}
        )
    ).json()

    deleted = await api_client.delete(f"/api/v1/cases/{case['id']}/notes/{note['id']}")
    assert deleted.status_code == 204
    assert (
        await api_client.get(f"/api/v1/cases/{case['id']}/notes/{note['id']}")
    ).status_code == 404
