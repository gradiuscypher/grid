import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from grid.db.base import Base
from grid.db.models.mixins import TimestampMixin, UUIDPkMixin


class TransformKind(enum.StrEnum):
    BUILTIN = "builtin"
    REMOTE = "remote"


class TransformRunStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Transform(UUIDPkMixin, TimestampMixin, Base):
    """Registry row for one transform (ARCHITECTURE §3/§6). Builtins are synced
    in from code descriptors at process startup (`services.transforms.
    sync_builtin_transforms`) rather than migrated in like entity types, since
    their manifest fields live with the implementation, not as static data.
    Remote transforms are registered by base URL and one row is upserted per
    descriptor in the fetched manifest.
    """

    __tablename__ = "transforms"

    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    kind: Mapped[TransformKind] = mapped_column(Enum(TransformKind, name="transform_kind"))
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(2000), default="")
    input_types: Mapped[list[str]] = mapped_column(JSONB, default=list)
    output_types: Mapped[list[str]] = mapped_column(JSONB, default=list)
    params_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    credential_names: Mapped[list[str]] = mapped_column(JSONB, default=list)
    timeout_s: Mapped[int] = mapped_column(Integer, default=30)
    rate_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # REMOTE only.
    base_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # Fernet-encrypted JSON blob of {credential_name: value}; never decrypted
    # outside the credential-resolution activity, never logged, never in events.
    credentials_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)


class TransformRun(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "transform_runs"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), index=True
    )
    transform_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("transforms.id"))
    status: Mapped[TransformRunStatus] = mapped_column(
        Enum(TransformRunStatus, name="transform_run_status"), default=TransformRunStatus.PENDING
    )
    triggered_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    input_node_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    result_node_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    result_edge_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    logs: Mapped[list[str]] = mapped_column(JSONB, default=list)
    error: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    temporal_workflow_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
