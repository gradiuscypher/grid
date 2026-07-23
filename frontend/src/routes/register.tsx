import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createRoute, Link, redirect, useNavigate } from '@tanstack/react-router'
import { type FormEvent, useState } from 'react'
import { meQueryOptions, registerRequest } from '../api/auth'
import { apiErrorMessage } from '../api/errors'
import { Button } from '../components/Button'
import { Panel } from '../components/Panel'
import { TextField } from '../components/TextField'
import styles from './AuthPage.module.css'
import { rootRoute } from './root'

export const registerRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/register',
  beforeLoad: async ({ context }) => {
    const user = await context.queryClient.ensureQueryData(meQueryOptions)
    if (user) throw redirect({ to: '/' })
  },
  component: RegisterPage,
})

function RegisterPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')

  const mutation = useMutation({
    mutationFn: registerRequest,
    onSuccess: (user) => {
      queryClient.setQueryData(meQueryOptions.queryKey, user)
      navigate({ to: '/' })
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    mutation.mutate({ email, display_name: displayName, password })
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.wordmark}>GRID</div>
      <Panel className={styles.panel}>
        <form className={styles.panel} onSubmit={handleSubmit}>
          <TextField
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <TextField
            label="Display name"
            type="text"
            autoComplete="name"
            required
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
          />
          <TextField
            label="Password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {mutation.isError && (
            <span className={styles.error} role="alert">
              {apiErrorMessage(mutation.error, 'Registration failed')}
            </span>
          )}
          <Button type="submit" variant="primary" disabled={mutation.isPending}>
            {mutation.isPending ? 'Creating account…' : 'Create account'}
          </Button>
        </form>
      </Panel>
      <span className={styles.footer}>
        Already have an account? <Link to="/login">Sign in</Link>
      </span>
    </div>
  )
}
