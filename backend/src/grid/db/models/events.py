import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Identity, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from grid.db.base import Base
from grid.db.models.mixins import UUIDPkMixin
from grid.db.models.provenance import CreatedVia


class Event(UUIDPkMixin, Base):
    """Append-only mutation log. `seq` is a globally monotonic identity column;
    clients replay a case's history filtered to `case_id` and ordered by `seq`.

    `seq` values are assigned at INSERT but only become visible at COMMIT, so
    under concurrent writers a later-assigned `seq` can commit before an
    earlier one — a `WHERE seq > :since ORDER BY seq` replay racing a commit
    could in theory advance past a lower `seq` that lands moments later.
    Not an issue at today's single-writer-per-case scale; worth revisiting
    (e.g. a short commit-visibility delay before treating a seq as "caught up")
    if concurrent writes to the same case become common."""

    __tablename__ = "events"

    seq: Mapped[int] = mapped_column(BigInteger, Identity(), unique=True, index=True)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), index=True
    )
    actor_type: Mapped[CreatedVia] = mapped_column(Enum(CreatedVia, name="event_actor_type"))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    actor_transform_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transform_runs.id"), nullable=True
    )
    actor_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
