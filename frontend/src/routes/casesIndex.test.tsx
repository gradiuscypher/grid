import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryHistory, createRouter, RouterProvider } from '@tanstack/react-router'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { routeTree } from './routeTree'

const mockUser = { id: 'user-1', email: 'a@example.com', display_name: 'A' }

vi.mock('../api/auth', () => ({
  meQueryOptions: {
    queryKey: ['auth', 'me'],
    queryFn: () => Promise.resolve(mockUser),
    retry: false,
  },
  loginRequest: vi.fn(),
  registerRequest: vi.fn(),
  logoutRequest: vi.fn(),
}))

const createCaseRequest = vi.fn(async (body: { name: string; description: string | null }) => ({
  id: 'case-1',
  name: body.name,
  description: body.description,
  created_by_user_id: mockUser.id,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
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
  createCaseRequest: (body: { name: string; description: string | null }) =>
    createCaseRequest(body),
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

describe('CasesIndexPage', () => {
  afterEach(() => {
    createCaseRequest.mockClear()
  })

  it('shows the empty state when there are no cases', async () => {
    renderAt('/')
    await waitFor(() => expect(screen.getByText(/no cases yet/i)).toBeInTheDocument())
  })

  it('submits the create-case form with the entered name and description', async () => {
    const user = userEvent.setup()
    renderAt('/')

    await waitFor(() => expect(screen.getByLabelText('Name')).toBeInTheDocument())
    await user.type(screen.getByLabelText('Name'), 'APT Tracking')
    await user.type(screen.getByLabelText(/description/i), 'Q3 campaign')
    await user.click(screen.getByRole('button', { name: /create case/i }))

    await waitFor(() =>
      expect(createCaseRequest).toHaveBeenCalledWith({
        name: 'APT Tracking',
        description: 'Q3 campaign',
      }),
    )
  })
})
