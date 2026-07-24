import enum
import uuid

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CreatedVia(enum.StrEnum):
    USER = "user"
    TRANSFORM = "transform"
    LLM = "llm"
    API = "api"


class ProvenanceMixin:
    """Mandatory provenance: who/what created this row, and the responsible actor.

    `created_by_conversation_id` has no FK constraint yet — `conversations` lands in
    Phase 4. The constraint gets added in a later additive migration once it exists,
    same as `created_by_transform_run_id` was until Phase 3a.
    """

    created_via: Mapped[CreatedVia] = mapped_column(Enum(CreatedVia, name="created_via"))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_by_transform_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transform_runs.id"), nullable=True
    )
    created_by_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
