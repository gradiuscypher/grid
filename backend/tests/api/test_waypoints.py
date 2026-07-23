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


async def test_waypoint_crud(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case = await _create_case(api_client)

    created = await api_client.post(
        f"/api/v1/cases/{case['id']}/waypoints",
        json={"name": "Home", "position_x": 0.0, "position_y": 0.0, "zoom": 1.0},
    )
    assert created.status_code == 201
    waypoint = created.json()

    updated = await api_client.patch(
        f"/api/v1/cases/{case['id']}/waypoints/{waypoint['id']}", json={"zoom": 2.5}
    )
    assert updated.status_code == 200
    assert updated.json()["zoom"] == 2.5

    listing = await api_client.get(f"/api/v1/cases/{case['id']}/waypoints")
    assert len(listing.json()) == 1

    deleted = await api_client.delete(f"/api/v1/cases/{case['id']}/waypoints/{waypoint['id']}")
    assert deleted.status_code == 204
    assert (
        await api_client.get(f"/api/v1/cases/{case['id']}/waypoints/{waypoint['id']}")
    ).status_code == 404
