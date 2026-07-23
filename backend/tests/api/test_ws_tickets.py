import httpx

from grid.events.tickets import redeem_ticket


async def _register(client: httpx.AsyncClient, email: str = "owner@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": email.split("@")[0], "password": "hunter2pass"},
    )
    assert response.status_code == 201
    return response.json()


async def test_ws_ticket_requires_auth(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post("/api/v1/ws-tickets")
    assert response.status_code == 401


async def test_ws_ticket_redeems_to_the_authenticated_user(api_client: httpx.AsyncClient) -> None:
    user = await _register(api_client)

    response = await api_client.post("/api/v1/ws-tickets")
    assert response.status_code == 200
    ticket = response.json()["ticket"]

    assert str(redeem_ticket(ticket)) == user["id"]
