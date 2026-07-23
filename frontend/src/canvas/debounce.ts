export interface Debounced<Args extends unknown[]> {
  (...args: Args): void
  cancel: () => void
  flush: () => void
}

/** Trailing-edge debounce that also exposes `flush` (call the pending
 * invocation immediately) — used to persist a node's final drop position the
 * instant a drag ends, instead of waiting out the debounce window. */
export function debounce<Args extends unknown[]>(
  fn: (...args: Args) => void,
  waitMs: number,
): Debounced<Args> {
  let timer: ReturnType<typeof setTimeout> | undefined
  let pendingArgs: Args | undefined

  const debounced = (...args: Args) => {
    pendingArgs = args
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      timer = undefined
      const toRun = pendingArgs
      pendingArgs = undefined
      if (toRun) fn(...toRun)
    }, waitMs)
  }

  debounced.cancel = () => {
    if (timer) clearTimeout(timer)
    timer = undefined
    pendingArgs = undefined
  }

  debounced.flush = () => {
    if (timer) clearTimeout(timer)
    timer = undefined
    const toRun = pendingArgs
    pendingArgs = undefined
    if (toRun) fn(...toRun)
  }

  return debounced
}
