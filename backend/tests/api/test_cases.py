from collections.abc import Awaitable, Callable

import httpx

ClientFactory = Callable[[], Awaitable[httpx.AsyncClient]]


async def _register(client: httpx.AsyncClient, email: str, password: str = "hunter2pass") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": email.split("@")[0], "password": password},
    )
    assert response.status_code == 201
    return response.json()


async def _create_case(client: httpx.AsyncClient, name: str = "Case A") -> dict:
    response = await client.post("/api/v1/cases", json={"name": name})
    assert response.status_code == 201
    return response.json()


async def test_creator_becomes_owner(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    case = await _create_case(owner)

    members = (await owner.get(f"/api/v1/cases/{case['id']}/members")).json()
    assert len(members) == 1
    assert members[0]["role"] == "owner"


async def test_viewer_can_read_but_not_add_member(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    case = await _create_case(owner)

    viewer = await api_client_factory()
    viewer_user = await _register(viewer, "viewer@example.com")

    add = await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": viewer_user["id"], "role": "viewer"},
    )
    assert add.status_code == 201

    assert (await viewer.get(f"/api/v1/cases/{case['id']}")).status_code == 200

    forbidden = await viewer.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": viewer_user["id"], "role": "editor"},
    )
    assert forbidden.status_code == 403


async def test_editor_can_read_but_not_manage_members(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    case = await _create_case(owner)

    editor = await api_client_factory()
    editor_user = await _register(editor, "editor@example.com")
    await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": editor_user["id"], "role": "editor"},
    )

    assert (await editor.get(f"/api/v1/cases/{case['id']}")).status_code == 200

    forbidden = await editor.delete(f"/api/v1/cases/{case['id']}/members/{editor_user['id']}")
    assert forbidden.status_code == 403


async def test_non_member_cannot_read_case(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    case = await _create_case(owner)

    outsider = await api_client_factory()
    await _register(outsider, "outsider@example.com")

    response = await outsider.get(f"/api/v1/cases/{case['id']}")
    assert response.status_code == 403


async def test_cannot_remove_last_owner(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    owner_user = await _register(owner, "owner@example.com")
    case = await _create_case(owner)

    response = await owner.delete(f"/api/v1/cases/{case['id']}/members/{owner_user['id']}")
    assert response.status_code == 403


async def test_editor_can_update_case(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    case = await _create_case(owner)

    editor = await api_client_factory()
    editor_user = await _register(editor, "editor@example.com")
    await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": editor_user["id"], "role": "editor"},
    )

    updated = await editor.patch(f"/api/v1/cases/{case['id']}", json={"name": "Renamed"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed"


async def test_viewer_cannot_update_case(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    case = await _create_case(owner)

    viewer = await api_client_factory()
    viewer_user = await _register(viewer, "viewer@example.com")
    await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": viewer_user["id"], "role": "viewer"},
    )

    response = await viewer.patch(f"/api/v1/cases/{case['id']}", json={"name": "Renamed"})
    assert response.status_code == 403


async def test_owner_can_delete_case(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    case = await _create_case(owner)

    deleted = await owner.delete(f"/api/v1/cases/{case['id']}")
    assert deleted.status_code == 204
    assert (await owner.get(f"/api/v1/cases/{case['id']}")).status_code == 403


async def test_editor_cannot_delete_case(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    case = await _create_case(owner)

    editor = await api_client_factory()
    editor_user = await _register(editor, "editor@example.com")
    await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": editor_user["id"], "role": "editor"},
    )

    response = await editor.delete(f"/api/v1/cases/{case['id']}")
    assert response.status_code == 403


async def test_cannot_demote_last_owner(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    owner_user = await _register(owner, "owner@example.com")
    case = await _create_case(owner)

    response = await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": owner_user["id"], "role": "viewer"},
    )
    assert response.status_code == 403

    members = (await owner.get(f"/api/v1/cases/{case['id']}/members")).json()
    assert members[0]["role"] == "owner"


async def test_can_demote_owner_when_another_owner_remains(
    api_client_factory: ClientFactory,
) -> None:
    owner = await api_client_factory()
    owner_user = await _register(owner, "owner@example.com")
    case = await _create_case(owner)

    second = await api_client_factory()
    second_user = await _register(second, "second-owner@example.com")
    await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": second_user["id"], "role": "owner"},
    )

    response = await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": owner_user["id"], "role": "viewer"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "viewer"


async def test_add_member_with_unknown_user_id_returns_404(
    api_client_factory: ClientFactory,
) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    case = await _create_case(owner)

    response = await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": "00000000-0000-0000-0000-000000000000", "role": "viewer"},
    )
    assert response.status_code == 404


async def test_read_only_api_key_cannot_create_case(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    key = (
        await owner.post("/api/v1/auth/api-keys", json={"name": "readonly-bot", "read_only": True})
    ).json()

    bearer_client = await api_client_factory()
    response = await bearer_client.post(
        "/api/v1/cases",
        json={"name": "Should Fail"},
        headers={"Authorization": f"Bearer {key['token']}"},
    )
    assert response.status_code == 403
