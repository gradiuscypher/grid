import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryHistory, createRouter, RouterProvider } from '@tanstack/react-router'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { routeTree } from './routeTree'

const state = vi.hoisted(() => ({
  user: null as { id: string; email: string; display_name: string } | null,
}))

const mockUser = { id: 'user-1', email: 'a@example.com', display_name: 'A' }

vi.mock('../api/auth', () => ({
  meQueryOptions: {
    queryKey: ['auth', 'me'],
    queryFn: () => Promise.resolve(state.user),
    retry: false,
  },
  loginRequest: vi.fn(async () => {
    state.user = mockUser
    return mockUser
  }),
  registerRequest: vi.fn(),
  logoutRequest: vi.fn(async () => {
    state.user = null
  }),
}))

vi.mock('../api/cases', () => ({
  casesQueryOptions: {
    queryKey: ['cases'],
    queryFn: () => Promise.resolve([]),
  },
  caseQueryOptions: () => ({
    queryKey: ['cases', 'unused'],
    queryFn: () => Promise.resolve(null),
  }),
  createCaseRequest: vi.fn(),
}))

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [path] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

describe('routing', () => {
  afterEach(() => {
    state.user = null
  })

  it('redirects an unauthenticated visitor from / to /login', async () => {
    const router = renderAt('/')
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
  })

  it('lets an authenticated user reach the case list', async () => {
    state.user = mockUser
    renderAt('/')
    await waitFor(() => expect(screen.getByText('Cases')).toBeInTheDocument())
    expect(screen.getByText('a@example.com')).toBeInTheDocument()
  })

  it('redirects an already-authenticated user away from /login', async () => {
    state.user = mockUser
    const router = renderAt('/login')
    await waitFor(() => expect(router.state.location.pathname).toBe('/'))
  })

  it('logs in and lands on the case list', async () => {
    const user = userEvent.setup()
    const router = renderAt('/login')

    await waitFor(() => expect(screen.getByLabelText('Email')).toBeInTheDocument())
    await user.type(screen.getByLabelText('Email'), 'a@example.com')
    await user.type(screen.getByLabelText('Password'), 'hunter22')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/'))
    expect(screen.getByText('Cases')).toBeInTheDocument()
  })

  it('logs out and returns to the login screen', async () => {
    state.user = mockUser
    const user = userEvent.setup()
    const router = renderAt('/')

    await waitFor(() => expect(screen.getByText('Cases')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /log out/i }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
  })
})
