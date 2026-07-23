import uuid

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from grid.db.base import Base
from grid.db.models.mixins import TimestampMixin, UUIDPkMixin
from grid.db.models.provenance import ProvenanceMixin


class Node(UUIDPkMixin, TimestampMixin, ProvenanceMixin, Base):
    __tablename__ = "nodes"
    __table_args__ = (
        UniqueConstraint("case_id", "entity_type_id", "canonical_value", name="uq_node_dedup"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), index=True
    )
    entity_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entity_types.id")
    )
    value: Mapped[str] = mapped_column(String(2000))
    canonical_value: Mapped[str] = mapped_column(String(2000))
    properties: Mapped[dict] = mapped_column(JSONB, default=dict)
    position_x: Mapped[float] = mapped_column(Float, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
