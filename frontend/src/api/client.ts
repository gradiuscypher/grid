import { QueryClient } from '@tanstack/react-query'
import { client } from './generated/client.gen'

// Cookie-authenticated requests need this header (CSRF mitigation, ARCHITECTURE §5:
// "SameSite=Lax + custom header requirement"; see Settings.client_header_name) — a
// simple cross-site form/fetch can't attach a custom header without CORS
// pre-approval from this server.
client.setConfig({ headers: { 'X-Grid-Client': 'web' } })

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
    },
  },
})
