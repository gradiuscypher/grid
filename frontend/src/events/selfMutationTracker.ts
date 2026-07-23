const TTL_MS = 5000

/** Tracks ids this browser *tab* mutated in the last few seconds, so
 * applyCaseEvent can skip a redundant re-fetch when the echoed WS event for
 * our own change comes back (we already have the authoritative response from
 * the mutation itself).
 *
 * Deliberately keyed by mutated id, not by actor_user_id: the same user can
 * have the same case open in two tabs (PLAN's Phase 2 exit criterion is
 * exactly this), and each tab needs the other tab's events applied even
 * though they share a user id. Module-scoped state is per-tab by
 * construction — each tab gets its own JS module instance. */
const recentlyMutated = new Map<string, number>()

export function markSelfMutated(id: string): void {
  recentlyMutated.set(id, Date.now() + TTL_MS)
}

export function wasSelfMutated(id: string): boolean {
  const expiresAt = recentlyMutated.get(id)
  if (expiresAt === undefined) return false
  if (expiresAt < Date.now()) {
    recentlyMutated.delete(id)
    return false
  }
  return true
}
