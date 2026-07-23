import uuid
from typing import Any

import jsonschema
from jsonschema.exceptions import SchemaError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from grid.db.models import EntityType, Node


def validate_json_schema(schema: dict[str, Any]) -> None:
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValidationError(f"invalid JSON Schema: {exc.message}") from exc


def validate_properties(entity_type: EntityType, properties: dict[str, Any]) -> None:
    validator = jsonschema.Draft202012Validator(entity_type.json_schema)
    errors = sorted(validator.iter_errors(properties), key=lambda e: list(e.path))
    if errors:
        messages = "; ".join(e.message for e in errors)
        raise ValidationError(f"properties do not match {entity_type.name!r} schema: {messages}")


async def list_entity_types(db: AsyncSession) -> list[EntityType]:
    result = await db.scalars(select(EntityType).order_by(EntityType.name))
    return list(result)


async def get_entity_type(db: AsyncSession, *, entity_type_id: uuid.UUID) -> EntityType:
    entity_type = await db.get(EntityType, entity_type_id)
    if entity_type is None:
        raise NotFoundError("entity type not found")
    return entity_type


async def create_entity_type(
    db: AsyncSession,
    *,
    name: str,
    display_name: str,
    json_schema: dict[str, Any],
    icon: str | None = None,
    color: str | None = None,
) -> EntityType:
    validate_json_schema(json_schema)
    existing = await db.scalar(select(EntityType).where(EntityType.name == name))
    if existing is not None:
        raise ConflictError(f"entity type {name!r} already exists")
    entity_type = EntityType(
        name=name,
        display_name=display_name,
        is_builtin=False,
        json_schema=json_schema,
        icon=icon,
        color=color,
    )
    db.add(entity_type)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(f"entity type {name!r} already exists") from exc
    await db.refresh(entity_type)
    return entity_type


async def update_entity_type(
    db: AsyncSession,
    *,
    entity_type_id: uuid.UUID,
    display_name: str | None = None,
    json_schema: dict[str, Any] | None = None,
    icon: str | None = None,
    color: str | None = None,
) -> EntityType:
    entity_type = await get_entity_type(db, entity_type_id=entity_type_id)
    if entity_type.is_builtin:
        raise ForbiddenError("builtin entity types cannot be modified")
    if json_schema is not None:
        validate_json_schema(json_schema)
        entity_type.json_schema = json_schema
    if display_name is not None:
        entity_type.display_name = display_name
    if icon is not None:
        entity_type.icon = icon
    if color is not None:
        entity_type.color = color
    await db.commit()
    await db.refresh(entity_type)
    return entity_type


async def delete_entity_type(db: AsyncSession, *, entity_type_id: uuid.UUID) -> None:
    entity_type = await get_entity_type(db, entity_type_id=entity_type_id)
    if entity_type.is_builtin:
        raise ForbiddenError("builtin entity types cannot be deleted")
    in_use = await db.scalar(select(Node.id).where(Node.entity_type_id == entity_type.id).limit(1))
    if in_use is not None:
        raise ConflictError("entity type is in use by existing nodes")
    await db.delete(entity_type)
    await db.commit()
