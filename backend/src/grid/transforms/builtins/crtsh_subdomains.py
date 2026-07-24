import httpx

from grid.transforms.base import BaseTransform
from grid.transforms.spec import (
    EntityRef,
    RunRequest,
    RunResult,
    RunResultEdge,
    RunResultNode,
    TransformDescriptor,
)


class CrtShSubdomainsTransform(BaseTransform):
    descriptor = TransformDescriptor(
        id="crtsh_subdomains",
        name="crt.sh Subdomain Discovery",
        version="1.0.0",
        description="Certificate-transparency subdomain discovery via crt.sh. Free, no key.",
        input_types=["domain"],
        output_types=["hostname"],
        timeout_s=30,
    )

    async def run(self, request: RunRequest) -> RunResult:
        nodes: list[RunResultNode] = []
        edges: list[RunResultEdge] = []
        logs: list[str] = []
        async with httpx.AsyncClient(timeout=25.0) as client:
            for inp in request.inputs:
                try:
                    resp = await client.get(
                        "https://crt.sh/", params={"q": f"%.{inp.value}", "output": "json"}
                    )
                    resp.raise_for_status()
                    entries = resp.json()
                except (httpx.HTTPError, ValueError) as exc:
                    logs.append(f"{inp.value}: crt.sh lookup failed: {exc}")
                    continue

                seen: set[str] = set()
                for entry in entries:
                    for raw_name in entry.get("name_value", "").split("\n"):
                        name = raw_name.strip().lower().removeprefix("*.")
                        if not name or name in seen:
                            continue
                        if name != inp.value and not name.endswith(f".{inp.value}"):
                            continue
                        seen.add(name)
                        if name == inp.value:
                            continue
                        nodes.append(RunResultNode(type="hostname", value=name))
                        edges.append(
                            RunResultEdge(
                                src=EntityRef(type=inp.type, value=inp.value),
                                dst=EntityRef(type="hostname", value=name),
                                relationship="has_subdomain",
                            )
                        )
                logs.append(f"{inp.value}: {len(seen)} unique names from crt.sh")
        return RunResult(nodes=nodes, edges=edges, logs=logs)
