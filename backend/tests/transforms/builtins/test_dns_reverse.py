import dns.asyncresolver
import dns.resolver
import pytest

from grid.transforms.builtins.dns_reverse import DnsReverseTransform
from grid.transforms.spec import RunRequest, TransformInput


class _FakePtrRdata:
    def __init__(self, target: str) -> None:
        self.target = target


async def test_dns_reverse_resolves_ptr(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_resolve_address(addr: str):
        return [_FakePtrRdata("Host.Example.com.")]

    monkeypatch.setattr(dns.asyncresolver, "resolve_address", fake_resolve_address)

    result = await DnsReverseTransform().run(
        RunRequest(inputs=[TransformInput(type="ipv4", value="93.184.216.34")])
    )

    assert len(result.nodes) == 1
    assert result.nodes[0].type == "hostname"
    assert result.nodes[0].value == "host.example.com"  # trailing dot stripped, lowercased
    assert result.edges[0].relationship == "resolves_to"


async def test_dns_reverse_logs_lookup_failures_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_resolve_address(addr: str):
        raise dns.resolver.NXDOMAIN()

    monkeypatch.setattr(dns.asyncresolver, "resolve_address", fake_resolve_address)

    result = await DnsReverseTransform().run(
        RunRequest(inputs=[TransformInput(type="ipv4", value="10.0.0.1")])
    )

    assert result.nodes == []
    assert len(result.logs) == 1
