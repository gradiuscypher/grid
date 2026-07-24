from typing import Any, ClassVar

import httpx
import pytest

import grid.transforms.builtins.crtsh_subdomains as crtsh_module
from grid.transforms.builtins.crtsh_subdomains import CrtShSubdomainsTransform
from grid.transforms.spec import RunRequest, TransformInput


class _FakeResponse:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        pass

    def json(self) -> list[dict[str, Any]]:
        return self._data


class _FakeAsyncClient:
    entries: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc: Any) -> bool:
        return False

    async def get(self, url: str, params: dict[str, str] | None = None) -> _FakeResponse:
        return _FakeResponse(self.entries)


class _FailingAsyncClient(_FakeAsyncClient):
    async def get(self, url: str, params: dict[str, str] | None = None) -> _FakeResponse:
        raise httpx.ConnectError("boom")


class _TimingOutAsyncClient(_FakeAsyncClient):
    async def get(self, url: str, params: dict[str, str] | None = None) -> _FakeResponse:
        raise httpx.ReadTimeout("")  # real crt.sh behavior observed against the dev stack


async def test_crtsh_subdomains_dedupes_and_strips_wildcards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeAsyncClient.entries = [
        {"name_value": "www.example.com\nmail.example.com"},
        {"name_value": "*.example.com"},
        {"name_value": "www.example.com"},  # duplicate across cert entries
        {"name_value": "notexample.com"},  # not a subdomain of example.com — filtered
    ]
    monkeypatch.setattr(crtsh_module.httpx, "AsyncClient", _FakeAsyncClient)

    result = await CrtShSubdomainsTransform().run(
        RunRequest(inputs=[TransformInput(type="domain", value="example.com")])
    )

    values = {n.value for n in result.nodes}
    assert values == {"www.example.com", "mail.example.com"}
    assert all(e.relationship == "has_subdomain" for e in result.edges)


async def test_crtsh_subdomains_logs_http_errors_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(crtsh_module.httpx, "AsyncClient", _FailingAsyncClient)

    result = await CrtShSubdomainsTransform().run(
        RunRequest(inputs=[TransformInput(type="domain", value="example.com")])
    )

    assert result.nodes == []
    assert "crt.sh lookup failed" in result.logs[0]


async def test_crtsh_subdomains_logs_exception_type_when_message_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(crtsh_module.httpx, "AsyncClient", _TimingOutAsyncClient)

    result = await CrtShSubdomainsTransform().run(
        RunRequest(inputs=[TransformInput(type="domain", value="example.com")])
    )

    assert result.logs[0] == "example.com: crt.sh lookup failed: ReadTimeout"
