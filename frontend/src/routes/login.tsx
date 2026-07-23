import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createRoute, Link, redirect, useNavigate } from '@tanstack/react-router'
import { type FormEvent, useState } from 'react'
import { loginRequest, meQueryOptions } from '../api/auth'
import { apiErrorMessage } from '../api/errors'
import { Button } from '../components/Button'
import { Panel } from '../components/Panel'
import { TextField } from '../components/TextField'
import styles from './AuthPage.module.css'
import { rootRoute } from './root'

export const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  beforeLoad: async ({ context }) => {
    const user = await context.queryClient.ensureQueryData(meQueryOptions)
    if (user) throw redirect({ to: '/' })
  },
  component: LoginPage,
})

function LoginPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const mutation = useMutation({
    mutationFn: loginRequest,
    onSuccess: (user) => {
      queryClient.setQueryData(meQueryOptions.queryKey, user)
      navigate({ to: '/' })
    },
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    mutation.mutate({ email, password })
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
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {mutation.isError && (
            <span className={styles.error} role="alert">
              {apiErrorMessage(mutation.error, 'Login failed')}
            </span>
          )}
          <Button type="submit" variant="primary" disabled={mutation.isPending}>
            {mutation.isPending ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </Panel>
      <span className={styles.footer}>
        No account? <Link to="/register">Register</Link>
      </span>
    </div>
  )
}
