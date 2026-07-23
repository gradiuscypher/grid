import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createRoute, Link, Outlet, redirect, useNavigate } from '@tanstack/react-router'
import { logoutRequest, meQueryOptions } from '../api/auth'
import { Button } from '../components/Button'
import { CommandPalette } from '../components/CommandPalette'
import { RouteError } from '../components/RouteError'
import { ThemeToggle } from '../components/ThemeToggle'
import styles from './AppShell.module.css'
import { rootRoute } from './root'

export const authedLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: '_authed',
  beforeLoad: async ({ context }) => {
    const user = await context.queryClient.ensureQueryData(meQueryOptions)
    if (!user) throw redirect({ to: '/login' })
    return { user }
  },
  component: AuthedLayout,
  errorComponent: RouteError,
})

function AuthedLayout() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: user } = useQuery(meQueryOptions)

  const logoutMutation = useMutation({
    mutationFn: logoutRequest,
    onSuccess: () => {
      queryClient.setQueryData(meQueryOptions.queryKey, null)
      navigate({ to: '/login' })
    },
  })

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Link to="/" className={styles.wordmark}>
          GRID
        </Link>
        <div className={styles.right}>
          {user && <span className={styles.email}>{user.email}</span>}
          <ThemeToggle />
          <Button
            variant="ghost"
            onClick={() => logoutMutation.mutate()}
            disabled={logoutMutation.isPending}
          >
            Log out
          </Button>
        </div>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
      <CommandPalette />
    </div>
  )
}
