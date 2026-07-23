import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grid.core.errors import NotFoundError, ValidationError
from grid.db.models import CaseRole, CreatedVia, Edge, Group, Node, Note, NoteTargetType, User
from grid.events.service import record_event
from grid.services.cases import require_role

_TARGET_MODELS = {
    NoteTargetType.NODE: Node,
    NoteTargetType.EDGE: Edge,
    NoteTargetType.GROUP: Group,
}


async def _require_target_in_case(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    target_type: NoteTargetType,
    target_id: uuid.UUID | None,
) -> None:
    if target_type == NoteTargetType.CASE:
        if target_id is not None:
            raise ValidationError("target_id must be omitted when target_type is 'case'")
        return
    if target_id is None:
        raise ValidationError(f"target_id is required when target_type is {target_type.value!r}")
    model = _TARGET_MODELS[target_type]
    target = await db.get(model, target_id)
    if target is None or target.case_id != case_id:
        raise ValidationError(f"{target_type.value} {target_id} does not exist in this case")


async def create_note(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    user: User,
    target_type: NoteTargetType,
    target_id: uuid.UUID | None,
    body: str,
) -> Note:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    await _require_target_in_case(db, case_id=case_id, target_type=target_type, target_id=target_id)
    note = Note(
        case_id=case_id,
        target_type=target_type,
        target_id=target_id,
        body=body,
        created_by_user_id=user.id,
    )
    db.add(note)
    await db.flush()
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="note.created",
        payload={
            "note_id": str(note.id),
            "target_type": target_type.value,
            "target_id": str(target_id) if target_id else None,
        },
    )
    await db.commit()
    await db.refresh(note)
    return note


async def get_note(db: AsyncSession, *, case_id: uuid.UUID, note_id: uuid.UUID, user: User) -> Note:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    note = await db.get(Note, note_id)
    if note is None or note.case_id != case_id:
        raise NotFoundError("note not found")
    return note


async def list_notes(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    user: User,
    target_type: NoteTargetType | None = None,
    target_id: uuid.UUID | None = None,
) -> list[Note]:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.VIEWER)
    stmt = select(Note).where(Note.case_id == case_id)
    if target_type is not None:
        stmt = stmt.where(Note.target_type == target_type)
    if target_id is not None:
        stmt = stmt.where(Note.target_id == target_id)
    result = await db.scalars(stmt)
    return list(result)


async def update_note(
    db: AsyncSession, *, case_id: uuid.UUID, note_id: uuid.UUID, user: User, body: str
) -> Note:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    note = await get_note(db, case_id=case_id, note_id=note_id, user=user)
    note.body = body
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="note.updated",
        payload={"note_id": str(note.id)},
    )
    await db.commit()
    await db.refresh(note)
    return note


async def delete_note(
    db: AsyncSession, *, case_id: uuid.UUID, note_id: uuid.UUID, user: User
) -> None:
    await require_role(db, case_id=case_id, user_id=user.id, minimum=CaseRole.EDITOR)
    note = await get_note(db, case_id=case_id, note_id=note_id, user=user)
    await record_event(
        db,
        case_id=case_id,
        actor_type=CreatedVia.USER,
        actor_user_id=user.id,
        type="note.deleted",
        payload={"note_id": str(note.id)},
    )
    await db.delete(note)
    await db.commit()
