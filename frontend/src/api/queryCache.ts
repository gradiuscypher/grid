/** Small helpers for patching TanStack Query list caches in place — shared by
 * our own mutations' onSuccess handlers and by the WS event patcher, so both
 * paths treat "insert or replace by id" / "remove by id" the same way. */

export function upsertById<T extends { id: string }>(list: T[], item: T): T[] {
  const index = list.findIndex((existing) => existing.id === item.id)
  if (index === -1) return [...list, item]
  const next = [...list]
  next[index] = item
  return next
}

export function removeByIds<T extends { id: string }>(list: T[], ids: ReadonlySet<string>): T[] {
  return list.filter((item) => !ids.has(item.id))
}
