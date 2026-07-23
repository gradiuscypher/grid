from collections.abc import Awaitable, Callable

import httpx


async def _register(
    client: httpx.AsyncClient, email: str = "alice@example.com", password: str = "hunter2pass"
) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": "Alice", "password": password},
    )


async def test_register_sets_session_cookie(api_client: httpx.AsyncClient) -> None:
    response = await _register(api_client)
    assert response.status_code == 201
    assert response.json()["email"] == "alice@example.com"
    assert "grid_session" in response.cookies


async def test_register_duplicate_email_conflicts(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    response = await _register(api_client)
    assert response.status_code == 409


async def test_login_wrong_password_unauthorized(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    response = await api_client.post(
        "/api/v1/auth/login", json={"email": "alice@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_me_requires_client_header(
    api_client_factory: Callable[[], Awaitable[httpx.AsyncClient]],
) -> None:
    client = await api_client_factory()
    await _register(client)
    client.headers.pop("X-Grid-Client")
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_without_cookie_unauthorized(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_lookup_finds_existing_user_by_email(
    api_client_factory: Callable[[], Awaitable[httpx.AsyncClient]],
) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")

    other = await api_client_factory()
    other_user = (await _register(other, "other@example.com")).json()

    response = await owner.get("/api/v1/auth/lookup", params={"email": "other@example.com"})
    assert response.status_code == 200
    assert response.json()["id"] == other_user["id"]


async def test_lookup_unknown_email_not_found(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    response = await api_client.get("/api/v1/auth/lookup", params={"email": "nobody@example.com"})
    assert response.status_code == 404


async def test_lookup_requires_auth(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/auth/lookup", params={"email": "alice@example.com"})
    assert response.status_code == 401


async def test_logout_invalidates_session(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    assert (await api_client.get("/api/v1/auth/me")).status_code == 200

    logout = await api_client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    response = await api_client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_api_key_auth_without_cookie(
    api_client_factory: Callable[[], Awaitable[httpx.AsyncClient]],
) -> None:
    owner = await api_client_factory()
    await _register(owner)

    created = await owner.post("/api/v1/auth/api-keys", json={"name": "ci-bot"})
    assert created.status_code == 201
    body = created.json()
    token = body["token"]
    assert token.startswith("grid_")
    assert token.startswith(body["key_prefix"])

    bearer_client = await api_client_factory()
    response = await bearer_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


async def test_revoked_api_key_rejected(
    api_client_factory: Callable[[], Awaitable[httpx.AsyncClient]],
) -> None:
    owner = await api_client_factory()
    await _register(owner)
    created = (await owner.post("/api/v1/auth/api-keys", json={"name": "ci-bot"})).json()

    await owner.delete(f"/api/v1/auth/api-keys/{created['id']}")

    bearer_client = await api_client_factory()
    response = await bearer_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {created['token']}"}
    )
    assert response.status_code == 401
