import uuid

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field

from grid.api.deps import CurrentActor, DbSession, WriteActor
from grid.db.models import Case, CaseMember, CaseRole
from grid.services import cases as case_service

router = APIRouter(prefix="/cases", tags=["cases"])


class CaseCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_by_user_id: uuid.UUID


class MemberAddRequest(BaseModel):
    user_id: uuid.UUID
    role: CaseRole


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: uuid.UUID
    user_id: uuid.UUID
    role: CaseRole


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
async def create_case(body: CaseCreateRequest, actor: WriteActor, db: DbSession) -> Case:
    return await case_service.create_case(
        db, user=actor.user, name=body.name, description=body.description
    )


@router.get("", response_model=list[CaseOut])
async def list_cases(actor: CurrentActor, db: DbSession) -> list[Case]:
    return await case_service.list_my_cases(db, user=actor.user)


@router.get("/{case_id}", response_model=CaseOut)
async def get_case(case_id: uuid.UUID, actor: CurrentActor, db: DbSession) -> Case:
    return await case_service.get_case(db, case_id=case_id, user=actor.user)


@router.get("/{case_id}/members", response_model=list[MemberOut])
async def list_members(case_id: uuid.UUID, actor: CurrentActor, db: DbSession) -> list[CaseMember]:
    return await case_service.list_members(db, case_id=case_id, user=actor.user)


@router.post("/{case_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def add_member(
    case_id: uuid.UUID, body: MemberAddRequest, actor: WriteActor, db: DbSession
) -> CaseMember:
    return await case_service.add_member(
        db, case_id=case_id, actor=actor.user, target_user_id=body.user_id, role=body.role
    )


@router.delete("/{case_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    case_id: uuid.UUID, user_id: uuid.UUID, actor: WriteActor, db: DbSession
) -> None:
    await case_service.remove_member(db, case_id=case_id, actor=actor.user, target_user_id=user_id)
