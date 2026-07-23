import { type FormEvent, useId, useState } from 'react'
import { apiErrorMessage } from '../api/errors'
import type { EntityTypeOut } from '../api/generated'
import { Button } from '../components/Button'
import { Select } from '../components/Select'
import { TextField } from '../components/TextField'
import styles from './CreateNodePanel.module.css'

interface CreateNodePanelProps {
  entityTypes: EntityTypeOut[]
  onCreate: (entityTypeId: string, value: string) => void
  isPending: boolean
  error: unknown
}

export function CreateNodePanel({ entityTypes, onCreate, isPending, error }: CreateNodePanelProps) {
  const [entityTypeId, setEntityTypeId] = useState(entityTypes[0]?.id ?? '')
  const [value, setValue] = useState('')
  const formId = useId()

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!entityTypeId || !value.trim()) return
    onCreate(entityTypeId, value.trim())
    setValue('')
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} aria-label="Create node">
      <Select
        label="Type"
        value={entityTypeId}
        onChange={(event) => setEntityTypeId(event.target.value)}
      >
        {entityTypes.map((entityType) => (
          <option key={entityType.id} value={entityType.id}>
            {entityType.display_name}
          </option>
        ))}
      </Select>
      <TextField
        label="Value"
        id={`${formId}-value`}
        placeholder="e.g. example.com"
        value={value}
        onChange={(event) => setValue(event.target.value)}
      />
      <Button type="submit" variant="primary" disabled={isPending || !value.trim()}>
        {isPending ? 'Adding…' : 'Add node'}
      </Button>
      {error !== null && error !== undefined && (
        <span className={styles.error} role="alert">
          {apiErrorMessage(error, 'Failed to create node')}
        </span>
      )}
    </form>
  )
}
