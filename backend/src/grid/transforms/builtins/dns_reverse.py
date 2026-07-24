import dns.asyncresolver
import dns.exception
import dns.resolver

from grid.transforms.base import BaseTransform
from grid.transforms.spec import (
    EntityRef,
    RunRequest,
    RunResult,
    RunResultEdge,
    RunResultNode,
    TransformDescriptor,
)

_LOOKUP_ERRORS = (
    dns.resolver.NoAnswer,
    dns.resolver.NXDOMAIN,
    dns.resolver.NoNameservers,
    dns.exception.Timeout,
)


class DnsReverseTransform(BaseTransform):
    descriptor = TransformDescriptor(
        id="dns_reverse",
        name="DNS Reverse Lookup",
        version="1.0.0",
        description="Resolve PTR records for an IPv4/IPv6 address.",
        input_types=["ipv4", "ipv6"],
        output_types=["hostname"],
        timeout_s=15,
    )

    async def run(self, request: RunRequest) -> RunResult:
        nodes: list[RunResultNode] = []
        edges: list[RunResultEdge] = []
        logs: list[str] = []
        for inp in request.inputs:
            try:
                answer = await dns.asyncresolver.resolve_address(inp.value)
            except _LOOKUP_ERRORS as exc:
                logs.append(f"{inp.value} PTR: {exc}")
                continue
            for rdata in answer:
                hostname = str(rdata.target).rstrip(".").lower()
                nodes.append(RunResultNode(type="hostname", value=hostname))
                edges.append(
                    RunResultEdge(
                        src=EntityRef(type=inp.type, value=inp.value),
                        dst=EntityRef(type="hostname", value=hostname),
                        relationship="resolves_to",
                    )
                )
        return RunResult(nodes=nodes, edges=edges, logs=logs)
