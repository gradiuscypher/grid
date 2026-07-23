import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { apiErrorMessage } from '../api/errors'
import type { NoteTargetType } from '../api/generated'
import { createNoteRequest, targetNotesQueryOptions } from '../api/notes'
import { Button } from '../components/Button'
import { TextArea } from '../components/TextArea'
import { markSelfMutated } from '../events/selfMutationTracker'
import styles from './NotesPanel.module.css'

interface NotesPanelProps {
  caseId: string
  targetType: NoteTargetType
  targetId: string
}

export function NotesPanel({ caseId, targetType, targetId }: NotesPanelProps) {
  const queryClient = useQueryClient()
  const notesQuery = useQuery(targetNotesQueryOptions(caseId, targetType, targetId))
  const [body, setBody] = useState('')

  const createNote = useMutation({
    mutationFn: (noteBody: string) => createNoteRequest(caseId, targetType, targetId, noteBody),
    onSuccess: (note) => {
      markSelfMutated(note.id)
      queryClient.invalidateQueries({
        queryKey: targetNotesQueryOptions(caseId, targetType, targetId).queryKey,
      })
      setBody('')
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!body.trim()) return
    createNote.mutate(body.trim())
  }

  return (
    <div className={styles.wrap}>
      <h3 className={styles.heading}>Notes</h3>
      {notesQuery.isLoading && <p className={styles.muted}>Loading notes…</p>}
      {notesQuery.data && notesQuery.data.length === 0 && (
        <p className={styles.muted}>No notes yet.</p>
      )}
      {notesQuery.data && notesQuery.data.length > 0 && (
        <ul className={styles.list}>
          {notesQuery.data.map((note) => (
            <li key={note.id} className={styles.note}>
              {note.body}
            </li>
          ))}
        </ul>
      )}
      <form className={styles.form} onSubmit={handleSubmit}>
        <TextArea
          label="Add a note"
          rows={3}
          value={body}
          onChange={(event) => setBody(event.target.value)}
          error={
            createNote.isError ? apiErrorMessage(createNote.error, 'Failed to add note') : undefined
          }
        />
        <Button type="submit" disabled={createNote.isPending || !body.trim()}>
          {createNote.isPending ? 'Adding…' : 'Add note'}
        </Button>
      </form>
    </div>
  )
}
