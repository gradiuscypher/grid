import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from grid.db.base import Base
from grid.db.models.mixins import TimestampMixin, UUIDPkMixin
from grid.db.models.provenance import ProvenanceMixin


class Edge(UUIDPkMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "edges"
    __table_args__ = (
        UniqueConstraint(
            "case_id", "src_node_id", "dst_node_id", "relationship", name="uq_edge_dedup"
        ),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), index=True
    )
    src_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nodes.id"))
    dst_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nodes.id"))
    relationship: Mapped[str] = mapped_column(String(200))
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    properties: Mapped[dict] = mapped_column(JSONB, default=dict)
