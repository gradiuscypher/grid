import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from '@tanstack/react-router'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { queryClient } from './api/client'
import { router } from './router'
import './theme/tokens.css'
import './theme/fonts.css'
import './index.css'

const rootElement = document.getElementById('root')
if (!rootElement) throw new Error('root element not found')

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
