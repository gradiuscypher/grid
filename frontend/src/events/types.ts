/** Wire shape from `events/service.py:serialize_event` — not part of the REST
 * OpenAPI schema (this rides the WS connection), so it's hand-typed here rather
 * than generated. */
export interface CaseEvent {
  seq: number
  case_id: string
  type: string
  actor_type: 'user' | 'transform' | 'llm' | 'api'
  actor_user_id: string | null
  payload: Record<string, unknown>
  created_at: string
}
