from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from grid.db.base import Base
from grid.db.models.mixins import TimestampMixin, UUIDPkMixin


class EntityType(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "entity_types"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    json_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
