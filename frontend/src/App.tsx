import { useEffect, useState } from 'react'

type HealthState =
  | { status: 'loading' }
  | { status: 'ok'; body: string }
  | { status: 'error'; message: string }

function useHealthz(): HealthState {
  const [state, setState] = useState<HealthState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false

    fetch('/api/v1/healthz')
      .then(async (res) => {
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
        return res.text()
      })
      .then((body) => {
        if (!cancelled) setState({ status: 'ok', body })
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({
            status: 'error',
            message: err instanceof Error ? err.message : String(err),
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  return state
}

function App() {
  const health = useHealthz()

  return (
    <main>
      <h1>Grid</h1>
      <p>
        API health: <span data-testid="health-status">{health.status}</span>
      </p>
      {health.status === 'ok' && <pre>{health.body}</pre>}
      {health.status === 'error' && <p role="alert">{health.message}</p>}
    </main>
  )
}

export default App
