import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createRoute, Link } from '@tanstack/react-router'
import { type FormEvent, useState } from 'react'
import { casesQueryOptions, createCaseRequest } from '../api/cases'
import { apiErrorMessage } from '../api/errors'
import { Button } from '../components/Button'
import { Panel } from '../components/Panel'
import { TextField } from '../components/TextField'
import { authedLayoutRoute } from './authed'
import styles from './CasesIndexPage.module.css'

export const casesIndexRoute = createRoute({
  getParentRoute: () => authedLayoutRoute,
  path: '/',
  component: CasesIndexPage,
})

function CasesIndexPage() {
  const casesQuery = useQuery(casesQueryOptions)
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const createMutation = useMutation({
    mutationFn: createCaseRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: casesQueryOptions.queryKey })
      setName('')
      setDescription('')
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    createMutation.mutate({ name, description: description || null })
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.heading}>
        <h1 className={styles.title}>Cases</h1>
      </div>

      {casesQuery.isLoading && <p>Loading cases…</p>}
      {casesQuery.isError && (
        <p className={styles.error} role="alert">
          {apiErrorMessage(casesQuery.error, 'Failed to load cases')}
        </p>
      )}
      {casesQuery.data && casesQuery.data.length === 0 && (
        <p className={styles.empty}>No cases yet — create one below.</p>
      )}
      {casesQuery.data && casesQuery.data.length > 0 && (
        <ul className={styles.list}>
          {casesQuery.data.map((c) => (
            <li key={c.id} className={styles.item}>
              <Link to="/cases/$caseId" params={{ caseId: c.id }} className={styles.itemLink}>
                <div className={styles.itemName}>{c.name}</div>
                {c.description && <div className={styles.itemDescription}>{c.description}</div>}
              </Link>
            </li>
          ))}
        </ul>
      )}

      <Panel>
        <form className={styles.form} onSubmit={handleSubmit}>
          <TextField
            label="Name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <TextField
            label="Description (optional)"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          {createMutation.isError && (
            <span className={styles.error} role="alert">
              {apiErrorMessage(createMutation.error, 'Failed to create case')}
            </span>
          )}
          <Button type="submit" variant="primary" disabled={createMutation.isPending}>
            {createMutation.isPending ? 'Creating…' : 'Create case'}
          </Button>
        </form>
      </Panel>
    </div>
  )
}
