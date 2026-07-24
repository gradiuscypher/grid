import dns.asyncresolver
import dns.resolver
import pytest

from grid.transforms.builtins.dns_forward import DnsForwardTransform
from grid.transforms.spec import RunRequest, TransformInput


async def test_dns_forward_resolves_a_and_aaaa(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_resolve(name: str, rdtype: str):
        if rdtype == "A":
            return ["93.184.216.34"]
        raise dns.resolver.NoAnswer()

    monkeypatch.setattr(dns.asyncresolver, "resolve", fake_resolve)

    result = await DnsForwardTransform().run(
        RunRequest(inputs=[TransformInput(type="domain", value="example.com")])
    )

    assert len(result.nodes) == 1
    assert result.nodes[0].type == "ipv4"
    assert result.nodes[0].value == "93.184.216.34"
    assert result.edges[0].relationship == "resolves_to"
    assert result.edges[0].src.value == "example.com"
    assert result.edges[0].dst.value == "93.184.216.34"


async def test_dns_forward_logs_lookup_failures_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_resolve(name: str, rdtype: str):
        raise dns.resolver.NXDOMAIN()

    monkeypatch.setattr(dns.asyncresolver, "resolve", fake_resolve)

    result = await DnsForwardTransform().run(
        RunRequest(inputs=[TransformInput(type="domain", value="nope.invalid")])
    )

    assert result.nodes == []
    assert result.edges == []
    assert len(result.logs) == 2  # A and AAAA both failed
