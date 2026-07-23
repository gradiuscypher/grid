import { useEffect } from 'react'
import { create } from 'zustand'

export interface PaletteCommand {
  id: string
  label: string
  shortcut?: string
  group?: string
  run: () => void
}

interface CommandRegistryState {
  registrations: Record<string, PaletteCommand[]>
  register: (key: string, commands: PaletteCommand[]) => void
  unregister: (key: string) => void
}

/** Foundation for the command palette's contextual actions (PLAN Phase 2b:
 * "shortcut registry foundation"). Route/feature components register a set of
 * commands under a stable key on mount and unregister on unmount, so the
 * palette (mounted once, in AuthedLayout) can show actions for whatever is
 * currently on screen without importing every feature module directly. */
export const useCommandRegistryStore = create<CommandRegistryState>((set) => ({
  registrations: {},
  register: (key, commands) =>
    set((state) => ({ registrations: { ...state.registrations, [key]: commands } })),
  unregister: (key) =>
    set((state) => {
      const next = { ...state.registrations }
      delete next[key]
      return { registrations: next }
    }),
}))

/** Registers `commands` under `key` for as long as the calling component is
 * mounted. Callers should memoize `commands` (e.g. `useMemo`) — a new array
 * identity on every render re-registers on every render. */
export function useRegisterCommands(key: string, commands: PaletteCommand[]): void {
  const register = useCommandRegistryStore((state) => state.register)
  const unregister = useCommandRegistryStore((state) => state.unregister)

  useEffect(() => {
    register(key, commands)
    return () => unregister(key)
  }, [key, commands, register, unregister])
}
