import { queryOptions } from '@tanstack/react-query'
import type { NoteOut, NoteTargetType } from './generated'
import { createNote, deleteNote, listNotes, updateNote } from './generated'

export function targetNotesQueryOptions(
  caseId: string,
  targetType: NoteTargetType,
  targetId: string,
) {
  return queryOptions({
    queryKey: ['cases', caseId, 'notes', targetType, targetId] as const,
    queryFn: async (): Promise<NoteOut[]> => {
      const { data, error } = await listNotes({
        path: { case_id: caseId },
        query: { target_type: targetType, target_id: targetId },
      })
      if (error) throw error
      return data
    },
  })
}

export async function createNoteRequest(
  caseId: string,
  targetType: NoteTargetType,
  targetId: string,
  body: string,
): Promise<NoteOut> {
  const { data, error } = await createNote({
    path: { case_id: caseId },
    body: { target_type: targetType, target_id: targetId, body },
  })
  if (error) throw error
  return data
}

export async function updateNoteRequest(
  caseId: string,
  noteId: string,
  body: string,
): Promise<NoteOut> {
  const { data, error } = await updateNote({
    path: { case_id: caseId, note_id: noteId },
    body: { body },
  })
  if (error) throw error
  return data
}

export async function deleteNoteRequest(caseId: string, noteId: string): Promise<void> {
  const { error } = await deleteNote({ path: { case_id: caseId, note_id: noteId } })
  if (error) throw error
}
