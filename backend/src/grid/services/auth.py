import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.config import get_settings
from grid.core.errors import ConflictError, NotFoundError, UnauthorizedError
from grid.core.security import generate_token, hash_password, hash_token, verify_password
from grid.db.models import ApiKey, AuthSession, User

API_KEY_PREFIX = "grid_"


async def register_user(db: AsyncSession, *, email: str, display_name: str, password: str) -> User:
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise ConflictError(f"email {email!r} is already registered")
    user = User(email=email, display_name=display_name, password_hash=hash_password(password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(f"email {email!r} is already registered") from exc
    await db.refresh(user)
    return user


async def lookup_user_by_email(db: AsyncSession, *, email: str) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active:
        raise NotFoundError(f"no user with email {email!r}")
    return user


async def authenticate_user(db: AsyncSession, *, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise UnauthorizedError("invalid email or password")
    return user


async def create_session(db: AsyncSession, *, user: User) -> tuple[AuthSession, str]:
    settings = get_settings()
    token = generate_token()
    session = AuthSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session, token


async def get_user_by_session_token(db: AsyncSession, *, token: str) -> User | None:
    session = await db.scalar(
        select(AuthSession).where(AuthSession.token_hash == hash_token(token))
    )
    if session is None or session.expires_at < datetime.now(UTC):
        return None
    user = await db.get(User, session.user_id)
    if user is None or not user.is_active:
        return None
    session.last_seen_at = datetime.now(UTC)
    await db.commit()
    return user


async def revoke_session(db: AsyncSession, *, token: str) -> None:
    session = await db.scalar(
        select(AuthSession).where(AuthSession.token_hash == hash_token(token))
    )
    if session is not None:
        await db.delete(session)
        await db.commit()


async def create_api_key(
    db: AsyncSession, *, user: User, name: str, read_only: bool = False
) -> tuple[ApiKey, str]:
    token = generate_token()
    raw_key = f"{API_KEY_PREFIX}{token}"
    key = ApiKey(
        user_id=user.id,
        name=name,
        key_hash=hash_token(token),
        key_prefix=raw_key[:8],
        read_only=read_only,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key, raw_key


async def get_user_by_api_key(db: AsyncSession, *, raw_key: str) -> tuple[User, ApiKey] | None:
    token = raw_key.removeprefix(API_KEY_PREFIX)
    key = await db.scalar(select(ApiKey).where(ApiKey.key_hash == hash_token(token)))
    if key is None or key.revoked_at is not None:
        return None
    user = await db.get(User, key.user_id)
    if user is None or not user.is_active:
        return None
    key.last_used_at = datetime.now(UTC)
    await db.commit()
    return user, key


async def list_api_keys(db: AsyncSession, *, user: User) -> list[ApiKey]:
    result = await db.scalars(select(ApiKey).where(ApiKey.user_id == user.id))
    return list(result)


async def revoke_api_key(db: AsyncSession, *, user: User, key_id: uuid.UUID) -> None:
    key = await db.get(ApiKey, key_id)
    if key is None or key.user_id != user.id:
        raise NotFoundError("API key not found")
    key.revoked_at = datetime.now(UTC)
    await db.commit()
