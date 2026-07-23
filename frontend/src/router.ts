import { createRouter } from '@tanstack/react-router'
import { queryClient } from './api/client'
import { routeTree } from './routes/routeTree'

export const router = createRouter({
  routeTree,
  context: { queryClient },
  defaultPreload: 'intent',
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
