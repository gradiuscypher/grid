"""Transform spec v1 (ARCHITECTURE §6): manifest + stateless run contract.

These models are the wire shape for both remote HTTP transforms (`GET
/.well-known/grid/transforms`, `POST /transforms/{id}/run`) and the internal
protocol builtins implement (`transforms.base.BaseTransform`) — one spec, two
transports, per ADR-007. A run response references graph entities by
`(type, value)` rather than internal node ids: transforms are stateless and must
not need to know Grid's ids, only the entities they were given and the ones they
discovered (`EntityRef` covers both an original input and a newly returned node).
"""

from typing import Any

from pydantic import BaseModel, Field


class TransformDescriptor(BaseModel):
    id: str
    name: str
    version: str
    description: str = ""
    input_types: list[str]
    output_types: list[str]
    params_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object"})
    credentials: list[str] = Field(default_factory=list)
    timeout_s: int = 30
    # Requests-per-minute the transform asks callers to respect. Captured for
    # manifest completeness; not yet enforced — see docs/IDEAS.md.
    rate_limit: int | None = None


class TransformManifest(BaseModel):
    transforms: list[TransformDescriptor]


class TransformInput(BaseModel):
    type: str
    value: str
    properties: dict[str, Any] = Field(default_factory=dict)


class RunRequest(BaseModel):
    inputs: list[TransformInput]
    params: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, str] = Field(default_factory=dict)


class EntityRef(BaseModel):
    type: str
    value: str


class RunResultNode(BaseModel):
    type: str
    value: str
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class RunResultEdge(BaseModel):
    src: EntityRef
    dst: EntityRef
    relationship: str
    label: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    nodes: list[RunResultNode] = Field(default_factory=list)
    edges: list[RunResultEdge] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
