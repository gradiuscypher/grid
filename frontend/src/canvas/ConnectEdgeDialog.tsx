import { type FormEvent, useState } from 'react'
import { apiErrorMessage } from '../api/errors'
import { Button } from '../components/Button'
import { Panel } from '../components/Panel'
import { TextField } from '../components/TextField'
import styles from './ConnectEdgeDialog.module.css'

export interface PendingConnection {
  sourceId: string
  targetId: string
  sourceLabel: string
  targetLabel: string
}

interface ConnectEdgeDialogProps {
  pending: PendingConnection
  onSubmit: (relationship: string, label: string | null) => void
  onCancel: () => void
  isPending: boolean
  error: unknown
}

export function ConnectEdgeDialog({
  pending,
  onSubmit,
  onCancel,
  isPending,
  error,
}: ConnectEdgeDialogProps) {
  const [relationship, setRelationship] = useState('')
  const [label, setLabel] = useState('')

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!relationship.trim()) return
    onSubmit(relationship.trim(), label.trim() || null)
  }

  return (
    // biome-ignore lint/a11y/noStaticElementInteractions: click-outside-to-cancel backdrop; Escape (onKeyDown below, bubbles up from the focused field) is the keyboard equivalent
    <div
      className={styles.overlay}
      onClick={onCancel}
      onKeyDown={(event) => {
        if (event.key === 'Escape') onCancel()
      }}
    >
      <Panel
        className={styles.dialog}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Connect nodes"
      >
        <h2 className={styles.title}>
          {pending.sourceLabel} → {pending.targetLabel}
        </h2>
        <form onSubmit={handleSubmit}>
          <TextField
            label="Relationship"
            required
            autoFocus
            placeholder="e.g. resolves_to"
            value={relationship}
            onChange={(event) => setRelationship(event.target.value)}
          />
          <TextField
            label="Label (optional)"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
          />
          {error !== null && error !== undefined && (
            <span className={styles.error} role="alert">
              {apiErrorMessage(error, 'Failed to create edge')}
            </span>
          )}
          <div className={styles.actions}>
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={isPending || !relationship.trim()}>
              {isPending ? 'Connecting…' : 'Connect'}
            </Button>
          </div>
        </form>
      </Panel>
    </div>
  )
}
