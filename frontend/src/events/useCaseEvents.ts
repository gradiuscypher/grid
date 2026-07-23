import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { createWsTicketRequest } from '../api/wsTicket'
import { applyCaseEvent } from './applyCaseEvent'
import type { CaseEvent } from './types'

const MAX_BACKOFF_MS = 15_000
const BASE_BACKOFF_MS = 500

function wsUrl(caseId: string, ticket: string, since: number): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/ws/cases/${caseId}?ticket=${encodeURIComponent(ticket)}&since=${since}`
}

/** Subscribes to the case's live event stream and patches the Query cache as
 * events arrive (ARCHITECTURE §4). Tickets are single-use and 30s-lived
 * (`events/tickets.py`), so a fresh one is minted on every connect/reconnect —
 * never reused across attempts. Reconnects with exponential backoff, resuming
 * from the last seen `seq` so the server replays anything missed. */
export function useCaseEvents(caseId: string, currentUserId: string | undefined): void {
  const queryClient = useQueryClient()
  const lastSeqRef = useRef(0)
  const seenSeqsRef = useRef<Set<number>>(new Set())

  useEffect(() => {
    let cancelled = false
    let socket: WebSocket | null = null
    let attempt = 0
    let retryTimer: ReturnType<typeof setTimeout> | undefined

    async function connect() {
      if (cancelled) return
      let ticket: string
      try {
        ticket = await createWsTicketRequest()
      } catch {
        scheduleReconnect()
        return
      }
      if (cancelled) return

      socket = new WebSocket(wsUrl(caseId, ticket, lastSeqRef.current))

      socket.onopen = () => {
        attempt = 0
      }

      socket.onmessage = (message) => {
        let event: CaseEvent
        try {
          event = JSON.parse(message.data as string) as CaseEvent
        } catch {
          return
        }
        if (seenSeqsRef.current.has(event.seq)) return
        seenSeqsRef.current.add(event.seq)
        lastSeqRef.current = Math.max(lastSeqRef.current, event.seq)
        void applyCaseEvent(queryClient, caseId, event, currentUserId)
      }

      socket.onclose = () => {
        if (!cancelled) scheduleReconnect()
      }
      socket.onerror = () => {
        socket?.close()
      }
    }

    function scheduleReconnect() {
      attempt += 1
      const delay = Math.min(BASE_BACKOFF_MS * 2 ** (attempt - 1), MAX_BACKOFF_MS)
      retryTimer = setTimeout(connect, delay)
    }

    void connect()

    return () => {
      cancelled = true
      if (retryTimer) clearTimeout(retryTimer)
      socket?.close()
    }
  }, [caseId, currentUserId, queryClient])
}
