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


class DnsForwardTransform(BaseTransform):
    descriptor = TransformDescriptor(
        id="dns_forward",
        name="DNS Forward Lookup",
        version="1.0.0",
        description="Resolve A/AAAA records for a domain or hostname.",
        input_types=["domain", "hostname"],
        output_types=["ipv4", "ipv6"],
        timeout_s=15,
    )

    async def run(self, request: RunRequest) -> RunResult:
        nodes: list[RunResultNode] = []
        edges: list[RunResultEdge] = []
        logs: list[str] = []
        for inp in request.inputs:
            for record_type, entity_type in (("A", "ipv4"), ("AAAA", "ipv6")):
                try:
                    answer = await dns.asyncresolver.resolve(inp.value, record_type)
                except _LOOKUP_ERRORS as exc:
                    logs.append(f"{inp.value} {record_type}: {exc}")
                    continue
                for rdata in answer:
                    ip = str(rdata)
                    nodes.append(RunResultNode(type=entity_type, value=ip))
                    edges.append(
                        RunResultEdge(
                            src=EntityRef(type=inp.type, value=inp.value),
                            dst=EntityRef(type=entity_type, value=ip),
                            relationship="resolves_to",
                        )
                    )
        return RunResult(nodes=nodes, edges=edges, logs=logs)
