from collections.abc import Awaitable, Callable

import httpx

ClientFactory = Callable[[], Awaitable[httpx.AsyncClient]]


async def _register(client: httpx.AsyncClient, email: str = "user@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": "User", "password": "hunter2pass"},
    )
    assert response.status_code == 201
    return response.json()


async def test_list_entity_types_requires_auth(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/entity-types")
    assert response.status_code == 401


async def test_create_list_and_delete_custom_entity_type(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)

    created = await api_client.post(
        "/api/v1/entity-types",
        json={
            "name": "crypto_wallet",
            "display_name": "Crypto Wallet",
            "json_schema": {"type": "object", "properties": {"chain": {"type": "string"}}},
        },
    )
    assert created.status_code == 201
    entity_type_id = created.json()["id"]

    listing = await api_client.get("/api/v1/entity-types")
    names = {et["name"] for et in listing.json()}
    assert "crypto_wallet" in names

    deleted = await api_client.delete(f"/api/v1/entity-types/{entity_type_id}")
    assert deleted.status_code == 204


async def test_create_entity_type_with_invalid_schema_rejected(
    api_client: httpx.AsyncClient,
) -> None:
    await _register(api_client)
    response = await api_client.post(
        "/api/v1/entity-types",
        json={"name": "bad", "display_name": "Bad", "json_schema": {"type": "not-a-real-type"}},
    )
    assert response.status_code == 422


async def test_duplicate_entity_type_name_conflicts(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    body = {"name": "crypto_wallet", "display_name": "Crypto Wallet", "json_schema": {}}
    assert (await api_client.post("/api/v1/entity-types", json=body)).status_code == 201
    assert (await api_client.post("/api/v1/entity-types", json=body)).status_code == 409


async def test_read_only_api_key_cannot_create_entity_type(
    api_client_factory: ClientFactory,
) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    key = (await owner.post("/api/v1/auth/api-keys", json={"name": "ro", "read_only": True})).json()

    bearer_client = await api_client_factory()
    response = await bearer_client.post(
        "/api/v1/entity-types",
        json={"name": "x", "display_name": "X", "json_schema": {}},
        headers={"Authorization": f"Bearer {key['token']}"},
    )
    assert response.status_code == 403
