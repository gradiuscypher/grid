import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.errors import ConflictError, ForbiddenError, ValidationError
from grid.db.models import EntityType
from grid.services import entity_types as entity_type_service

ASN_SCHEMA = {
    "type": "object",
    "required": ["number"],
    "properties": {"number": {"type": "integer"}},
}


def test_validate_json_schema_accepts_valid_schema() -> None:
    entity_type_service.validate_json_schema(ASN_SCHEMA)


def test_validate_json_schema_rejects_malformed_schema() -> None:
    with pytest.raises(ValidationError):
        entity_type_service.validate_json_schema({"type": "not-a-real-type"})


def test_validate_properties_accepts_matching_properties() -> None:
    entity_type = EntityType(name="asn", display_name="ASN", json_schema=ASN_SCHEMA)
    entity_type_service.validate_properties(entity_type, {"number": 12345})


def test_validate_properties_rejects_missing_required_field() -> None:
    entity_type = EntityType(name="asn", display_name="ASN", json_schema=ASN_SCHEMA)
    with pytest.raises(ValidationError):
        entity_type_service.validate_properties(entity_type, {})


async def test_create_and_get_custom_entity_type(db_session: AsyncSession) -> None:
    created = await entity_type_service.create_entity_type(
        db_session,
        name="crypto_wallet",
        display_name="Crypto Wallet",
        json_schema={"type": "object"},
    )
    assert created.is_builtin is False

    fetched = await entity_type_service.get_entity_type(db_session, entity_type_id=created.id)
    assert fetched.name == "crypto_wallet"


async def test_create_entity_type_rejects_duplicate_name(db_session: AsyncSession) -> None:
    await entity_type_service.create_entity_type(
        db_session, name="crypto_wallet", display_name="Crypto Wallet", json_schema={}
    )
    with pytest.raises(ConflictError):
        await entity_type_service.create_entity_type(
            db_session, name="crypto_wallet", display_name="Again", json_schema={}
        )


async def test_create_entity_type_rejects_invalid_schema(db_session: AsyncSession) -> None:
    with pytest.raises(ValidationError):
        await entity_type_service.create_entity_type(
            db_session, name="bad", display_name="Bad", json_schema={"type": "not-a-real-type"}
        )


async def test_builtin_entity_type_cannot_be_modified_or_deleted(db_session: AsyncSession) -> None:
    # Not "domain"/etc — conftest's `test_engine` pre-seeds the real ARCHITECTURE §3
    # builtins, so this uses a name that can't collide with them.
    builtin = EntityType(
        name="test_widget",
        display_name="Test Widget",
        is_builtin=True,
        json_schema={"type": "object"},
    )
    db_session.add(builtin)
    await db_session.commit()
    await db_session.refresh(builtin)

    with pytest.raises(ForbiddenError):
        await entity_type_service.update_entity_type(
            db_session, entity_type_id=builtin.id, display_name="Nope"
        )
    with pytest.raises(ForbiddenError):
        await entity_type_service.delete_entity_type(db_session, entity_type_id=builtin.id)
