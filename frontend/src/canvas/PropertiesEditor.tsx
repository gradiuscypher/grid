import { useState } from 'react'
import { apiErrorMessage } from '../api/errors'
import { Button } from '../components/Button'
import { TextArea } from '../components/TextArea'

interface PropertiesEditorProps {
  initial: Record<string, unknown>
  onSave: (properties: Record<string, unknown>) => void
  isPending: boolean
  error: unknown
}

/** JSON textarea for the `properties` bag (ARCHITECTURE §3). Builtin entity
 * types currently seed an empty `{"type": "object"}` JSON Schema (no declared
 * fields), so there's nothing yet for a schema-driven form to key off — this
 * editor works for any schema since the server re-validates on save. */
export function PropertiesEditor({ initial, onSave, isPending, error }: PropertiesEditorProps) {
  const [text, setText] = useState(() => JSON.stringify(initial, null, 2))
  const [parseError, setParseError] = useState<string | null>(null)

  function handleSave() {
    try {
      const parsed = JSON.parse(text)
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        setParseError('Properties must be a JSON object')
        return
      }
      setParseError(null)
      onSave(parsed as Record<string, unknown>)
    } catch {
      setParseError('Invalid JSON')
    }
  }

  return (
    <div>
      <TextArea
        label="Properties"
        rows={8}
        value={text}
        onChange={(event) => setText(event.target.value)}
        error={
          parseError ?? (error ? apiErrorMessage(error, 'Failed to save properties') : undefined)
        }
      />
      <Button type="button" onClick={handleSave} disabled={isPending}>
        {isPending ? 'Saving…' : 'Save properties'}
      </Button>
    </div>
  )
}
