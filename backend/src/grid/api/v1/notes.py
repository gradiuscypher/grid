import uuid

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field

from grid.api.deps import CurrentActor, DbSession, WriteActor
from grid.db.models import Note, NoteTargetType
from grid.services import notes as note_service

router = APIRouter(prefix="/cases/{case_id}/notes", tags=["notes"])


class NoteCreateRequest(BaseModel):
    target_type: NoteTargetType
    target_id: uuid.UUID | None = None
    body: str = Field(min_length=1)


class NoteUpdateRequest(BaseModel):
    body: str = Field(min_length=1)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    target_type: NoteTargetType
    target_id: uuid.UUID | None
    body: str
    created_by_user_id: uuid.UUID


@router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    case_id: uuid.UUID, body: NoteCreateRequest, actor: WriteActor, db: DbSession
) -> Note:
    return await note_service.create_note(
        db,
        case_id=case_id,
        user=actor.user,
        target_type=body.target_type,
        target_id=body.target_id,
        body=body.body,
    )


@router.get("", response_model=list[NoteOut])
async def list_notes(
    case_id: uuid.UUID,
    actor: CurrentActor,
    db: DbSession,
    target_type: NoteTargetType | None = None,
    target_id: uuid.UUID | None = None,
) -> list[Note]:
    return await note_service.list_notes(
        db, case_id=case_id, user=actor.user, target_type=target_type, target_id=target_id
    )


@router.get("/{note_id}", response_model=NoteOut)
async def get_note(
    case_id: uuid.UUID, note_id: uuid.UUID, actor: CurrentActor, db: DbSession
) -> Note:
    return await note_service.get_note(db, case_id=case_id, note_id=note_id, user=actor.user)


@router.patch("/{note_id}", response_model=NoteOut)
async def update_note(
    case_id: uuid.UUID,
    note_id: uuid.UUID,
    body: NoteUpdateRequest,
    actor: WriteActor,
    db: DbSession,
) -> Note:
    return await note_service.update_note(
        db, case_id=case_id, note_id=note_id, user=actor.user, body=body.body
    )


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    case_id: uuid.UUID, note_id: uuid.UUID, actor: WriteActor, db: DbSession
) -> None:
    await note_service.delete_note(db, case_id=case_id, note_id=note_id, user=actor.user)
