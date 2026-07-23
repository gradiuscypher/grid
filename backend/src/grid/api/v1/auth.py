import uuid
from datetime import datetime

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from grid.api.deps import CurrentActor, DbSession, WriteActor
from grid.core.config import get_settings
from grid.db.models import ApiKey, User
from grid.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    read_only: bool = False


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    read_only: bool
    last_used_at: datetime | None
    revoked_at: datetime | None


class ApiKeyCreatedOut(ApiKeyOut):
    token: str


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
    )


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    operation_id="register",
)
async def register(body: RegisterRequest, db: DbSession, response: Response) -> User:
    user = await auth_service.register_user(
        db, email=body.email, display_name=body.display_name, password=body.password
    )
    _, token = await auth_service.create_session(db, user=user)
    _set_session_cookie(response, token)
    return user


@router.post("/login", response_model=UserOut, operation_id="login")
async def login(body: LoginRequest, db: DbSession, response: Response) -> User:
    user = await auth_service.authenticate_user(db, email=body.email, password=body.password)
    _, token = await auth_service.create_session(db, user=user)
    _set_session_cookie(response, token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, operation_id="logout")
async def logout(request: Request, db: DbSession, response: Response) -> None:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await auth_service.revoke_session(db, token=token)
    response.delete_cookie(settings.session_cookie_name)


@router.get("/me", response_model=UserOut, operation_id="get_me")
async def me(actor: CurrentActor) -> User:
    return actor.user


@router.post(
    "/api-keys",
    response_model=ApiKeyCreatedOut,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_api_key",
)
async def create_api_key(
    body: ApiKeyCreateRequest, actor: WriteActor, db: DbSession
) -> ApiKeyCreatedOut:
    key, token = await auth_service.create_api_key(
        db, user=actor.user, name=body.name, read_only=body.read_only
    )
    return ApiKeyCreatedOut(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        read_only=key.read_only,
        last_used_at=key.last_used_at,
        revoked_at=key.revoked_at,
        token=token,
    )


@router.get("/api-keys", response_model=list[ApiKeyOut], operation_id="list_api_keys")
async def list_api_keys(actor: CurrentActor, db: DbSession) -> list[ApiKey]:
    return await auth_service.list_api_keys(db, user=actor.user)


@router.delete(
    "/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="revoke_api_key"
)
async def revoke_api_key(key_id: uuid.UUID, actor: WriteActor, db: DbSession) -> None:
    await auth_service.revoke_api_key(db, user=actor.user, key_id=key_id)
