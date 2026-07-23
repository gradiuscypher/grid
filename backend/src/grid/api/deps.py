from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.config import get_settings
from grid.db.models import User
from grid.db.session import get_session
from grid.services import auth as auth_service

DbSession = Annotated[AsyncSession, Depends(get_session)]


@dataclass
class Actor:
    user: User
    read_only: bool = False


async def get_current_actor(
    request: Request,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> Actor:
    settings = get_settings()

    if authorization is not None and authorization.startswith("Bearer "):
        raw_key = authorization.removeprefix("Bearer ").strip()
        result = await auth_service.get_user_by_api_key(db, raw_key=raw_key)
        if result is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid API key")
        user, key = result
        return Actor(user=user, read_only=key.read_only)

    token = request.cookies.get(settings.session_cookie_name)
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")

    # CSRF mitigation (ARCHITECTURE §5): a simple cross-site form/fetch can't
    # attach a custom header without CORS pre-approval from this server.
    if request.headers.get(settings.client_header_name) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing client header")

    user = await auth_service.get_user_by_session_token(db, token=token)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session expired or invalid")
    return Actor(user=user)


CurrentActor = Annotated[Actor, Depends(get_current_actor)]


async def require_write_actor(actor: CurrentActor) -> Actor:
    if actor.read_only:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "API key is read-only")
    return actor


WriteActor = Annotated[Actor, Depends(require_write_actor)]
