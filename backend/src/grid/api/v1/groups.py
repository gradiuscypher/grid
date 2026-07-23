import uuid

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field

from grid.api.deps import CurrentActor, DbSession, WriteActor
from grid.db.models import Group
from grid.services import groups as group_service

router = APIRouter(prefix="/cases/{case_id}/groups", tags=["groups"])


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    context_note: str | None = None
    color: str | None = Field(default=None, max_length=20)


class GroupUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    context_note: str | None = None
    color: str | None = Field(default=None, max_length=20)


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    name: str
    context_note: str | None
    color: str | None
    created_by_user_id: uuid.UUID


class GroupMemberAddRequest(BaseModel):
    node_id: uuid.UUID


@router.post(
    "", response_model=GroupOut, status_code=status.HTTP_201_CREATED, operation_id="create_group"
)
async def create_group(
    case_id: uuid.UUID, body: GroupCreateRequest, actor: WriteActor, db: DbSession
) -> Group:
    return await group_service.create_group(
        db,
        case_id=case_id,
        user=actor.user,
        name=body.name,
        context_note=body.context_note,
        color=body.color,
    )


@router.get("", response_model=list[GroupOut], operation_id="list_groups")
async def list_groups(case_id: uuid.UUID, actor: CurrentActor, db: DbSession) -> list[Group]:
    return await group_service.list_groups(db, case_id=case_id, user=actor.user)


@router.get("/{group_id}", response_model=GroupOut, operation_id="get_group")
async def get_group(
    case_id: uuid.UUID, group_id: uuid.UUID, actor: CurrentActor, db: DbSession
) -> Group:
    return await group_service.get_group(db, case_id=case_id, group_id=group_id, user=actor.user)


@router.patch("/{group_id}", response_model=GroupOut, operation_id="update_group")
async def update_group(
    case_id: uuid.UUID,
    group_id: uuid.UUID,
    body: GroupUpdateRequest,
    actor: WriteActor,
    db: DbSession,
) -> Group:
    return await group_service.update_group(
        db,
        case_id=case_id,
        group_id=group_id,
        user=actor.user,
        name=body.name,
        context_note=body.context_note,
        color=body.color,
    )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="delete_group")
async def delete_group(
    case_id: uuid.UUID, group_id: uuid.UUID, actor: WriteActor, db: DbSession
) -> None:
    await group_service.delete_group(db, case_id=case_id, group_id=group_id, user=actor.user)


@router.get(
    "/{group_id}/members", response_model=list[uuid.UUID], operation_id="list_group_members"
)
async def list_group_members(
    case_id: uuid.UUID, group_id: uuid.UUID, actor: CurrentActor, db: DbSession
) -> list[uuid.UUID]:
    return await group_service.list_group_members(
        db, case_id=case_id, group_id=group_id, user=actor.user
    )


@router.post(
    "/{group_id}/members",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="add_group_member",
)
async def add_group_member(
    case_id: uuid.UUID,
    group_id: uuid.UUID,
    body: GroupMemberAddRequest,
    actor: WriteActor,
    db: DbSession,
) -> None:
    await group_service.add_group_member(
        db, case_id=case_id, group_id=group_id, user=actor.user, node_id=body.node_id
    )


@router.delete(
    "/{group_id}/members/{node_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="remove_group_member",
)
async def remove_group_member(
    case_id: uuid.UUID, group_id: uuid.UUID, node_id: uuid.UUID, actor: WriteActor, db: DbSession
) -> None:
    await group_service.remove_group_member(
        db, case_id=case_id, group_id=group_id, user=actor.user, node_id=node_id
    )
