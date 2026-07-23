"""seed builtin entity types

Revision ID: 244e9746d9db
Revises: ea42ef050af7
Create Date: 2026-07-23 06:36:04.496550

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "244e9746d9db"
down_revision: str | Sequence[str] | None = "ea42ef050af7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Decoupled from the ORM model on purpose (ARCHITECTURE §3 builtin list) — this
# migration must keep working even if grid.db.models.entity_types changes shape later.
entity_types_table = sa.table(
    "entity_types",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("display_name", sa.String),
    sa.column("is_builtin", sa.Boolean),
    sa.column("json_schema", postgresql.JSONB),
    sa.column("icon", sa.String),
    sa.column("color", sa.String),
)

# (name, display_name, icon, color)
BUILTINS: list[tuple[str, str, str, str]] = [
    ("domain", "Domain", "globe", "#4f8cff"),
    ("hostname", "Hostname", "server", "#4f8cff"),
    ("ipv4", "IPv4 Address", "hard-drive", "#22a06b"),
    ("ipv6", "IPv6 Address", "hard-drive", "#22a06b"),
    ("cidr", "CIDR Block", "network", "#22a06b"),
    ("asn", "ASN", "share-2", "#22a06b"),
    ("url", "URL", "link", "#a855f7"),
    ("email", "Email Address", "mail", "#f59e0b"),
    ("username", "Username", "at-sign", "#f59e0b"),
    ("person", "Person", "user", "#ef4444"),
    ("organization", "Organization", "building", "#ef4444"),
    ("hash", "Hash", "hash", "#6b7280"),
    ("note", "Note", "file-text", "#eab308"),
]


def upgrade() -> None:
    op.bulk_insert(
        entity_types_table,
        [
            {
                "id": uuid.uuid4(),
                "name": name,
                "display_name": display_name,
                "is_builtin": True,
                "json_schema": {"type": "object"},
                "icon": icon,
                "color": color,
            }
            for name, display_name, icon, color in BUILTINS
        ],
    )


def downgrade() -> None:
    names = [name for name, *_ in BUILTINS]
    op.execute(
        entity_types_table.delete().where(entity_types_table.c.name.in_(names))
    )
