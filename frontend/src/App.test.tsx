import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

describe('App', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows API health once the healthz fetch resolves', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: () => Promise.resolve('{"status":"ok"}'),
      }),
    )

    render(<App />)

    await waitFor(() => expect(screen.getByTestId('health-status')).toHaveTextContent('ok'))
  })

  it('surfaces an error when the healthz fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))

    render(<App />)

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('network down'))
  })
})
