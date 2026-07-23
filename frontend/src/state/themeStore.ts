import { create } from 'zustand'

export type Theme = 'light' | 'dark'

// index.html has an inline pre-hydration copy of this fallback logic (it must run
// before any JS module loads, so it can't import this file) — keep both in sync.
const STORAGE_KEY = 'grid-theme'

function systemTheme(): Theme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function initialTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY)
  return stored === 'light' || stored === 'dark' ? stored : systemTheme()
}

function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme
  localStorage.setItem(STORAGE_KEY, theme)
}

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: initialTheme(),
  setTheme: (theme) => {
    applyTheme(theme)
    set({ theme })
  },
  toggleTheme: () => {
    const next: Theme = get().theme === 'light' ? 'dark' : 'light'
    applyTheme(next)
    set({ theme: next })
  },
}))
