import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from grid.db.base import Base
from grid.db.models.mixins import TimestampMixin, UUIDPkMixin


class NoteTargetType(enum.StrEnum):
    CASE = "case"
    NODE = "node"
    EDGE = "edge"
    GROUP = "group"


class Note(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "notes"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), index=True
    )
    target_type: Mapped[NoteTargetType] = mapped_column(
        Enum(NoteTargetType, name="note_target_type")
    )
    # Null when target_type == CASE (the note is attached to the case itself).
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
