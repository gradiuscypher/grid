from collections.abc import Awaitable, Callable

import httpx
import pytest

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


async def _transform_id(client: httpx.AsyncClient, slug: str) -> str:
    listing = (await client.get("/api/v1/transforms")).json()
    return next(t["id"] for t in listing if t["slug"] == slug)


async def test_list_transforms_filters_by_input_type(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    domain_only = (
        await api_client.get("/api/v1/transforms", params={"input_type": "domain"})
    ).json()
    slugs = {t["slug"] for t in domain_only}
    assert "crtsh_subdomains" in slugs
    assert "dns_reverse" not in slugs  # takes ipv4/ipv6, not domain


async def test_get_transform_by_id(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    transform_id = await _transform_id(api_client, "dns_forward")
    response = await api_client.get(f"/api/v1/transforms/{transform_id}")
    assert response.status_code == 200
    assert response.json()["slug"] == "dns_forward"


async def test_run_transform_rejects_input_type_mismatch(api_client: httpx.AsyncClient) -> None:
    await _register(api_client)
    case = await _create_case(api_client)
    ipv4_type = await _entity_type_id(api_client, "ipv4")
    node = (
        await api_client.post(
            f"/api/v1/cases/{case['id']}/nodes",
            json={"entity_type_id": ipv4_type, "value": "1.2.3.4"},
        )
    ).json()
    crtsh_id = await _transform_id(api_client, "crtsh_subdomains")  # takes "domain"

    response = await api_client.post(
        f"/api/v1/cases/{case['id']}/transform-runs",
        json={"transform_id": crtsh_id, "input_node_ids": [node["id"]]},
    )
    assert response.status_code == 422


async def test_run_transform_when_temporal_unreachable_lands_run_failed(
    api_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`workflows.launch`'s fallback path: this deliberately doesn't depend on
    whether a real Temporal happens to be reachable from wherever tests run (a
    `make dev` stack on the same host publishes :7233, so it might be!) — that
    would also mean a real workflow executing real activities against the *dev*
    database, not this test's isolated one. Forcing the failure instead keeps the
    test deterministic and never risks touching real data."""

    async def _unreachable() -> None:
        raise ConnectionError("no temporal reachable in tests")

    monkeypatch.setattr("grid.workflows.launch.get_temporal_client", _unreachable)

    await _register(api_client)
    case = await _create_case(api_client)
    domain_type = await _entity_type_id(api_client, "domain")
    node = (
        await api_client.post(
            f"/api/v1/cases/{case['id']}/nodes",
            json={"entity_type_id": domain_type, "value": "example.com"},
        )
    ).json()
    dns_forward_id = await _transform_id(api_client, "dns_forward")

    response = await api_client.post(
        f"/api/v1/cases/{case['id']}/transform-runs",
        json={"transform_id": dns_forward_id, "input_node_ids": [node["id"]]},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert "could not start workflow" in body["error"]

    listing = await api_client.get(f"/api/v1/cases/{case['id']}/transform-runs")
    assert len(listing.json()) == 1
    assert listing.json()[0]["id"] == body["id"]


async def test_viewer_cannot_run_transform(api_client_factory: ClientFactory) -> None:
    owner = await api_client_factory()
    await _register(owner, "owner@example.com")
    case = await _create_case(owner)
    domain_type = await _entity_type_id(owner, "domain")
    node = (
        await owner.post(
            f"/api/v1/cases/{case['id']}/nodes",
            json={"entity_type_id": domain_type, "value": "example.com"},
        )
    ).json()
    dns_forward_id = await _transform_id(owner, "dns_forward")

    viewer = await api_client_factory()
    viewer_user = await _register(viewer, "viewer@example.com")
    await owner.post(
        f"/api/v1/cases/{case['id']}/members",
        json={"user_id": viewer_user["id"], "role": "viewer"},
    )

    response = await viewer.post(
        f"/api/v1/cases/{case['id']}/transform-runs",
        json={"transform_id": dns_forward_id, "input_node_ids": [node["id"]]},
    )
    assert response.status_code == 403
