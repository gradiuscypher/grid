import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from grid.db.base import Base
from grid.db.models.mixins import TimestampMixin, UUIDPkMixin


class CaseRole(enum.StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


# Ordered weakest to strongest so `ROLE_RANK[role] >= ROLE_RANK[required]` checks work.
ROLE_RANK: dict[CaseRole, int] = {
    CaseRole.VIEWER: 0,
    CaseRole.EDITOR: 1,
    CaseRole.OWNER: 2,
}


class Case(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "cases"

    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )


class CaseMember(Base):
    __tablename__ = "case_members"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    role: Mapped[CaseRole] = mapped_column(Enum(CaseRole, name="case_role"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
