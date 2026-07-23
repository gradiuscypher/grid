import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

describe('themeStore', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    vi.resetModules()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('falls back to system preference when nothing is stored', async () => {
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true } as MediaQueryList))
    const { useThemeStore } = await import('./themeStore')
    expect(useThemeStore.getState().theme).toBe('dark')
  })

  it('prefers a stored theme over system preference', async () => {
    localStorage.setItem('grid-theme', 'light')
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true } as MediaQueryList))
    const { useThemeStore } = await import('./themeStore')
    expect(useThemeStore.getState().theme).toBe('light')
  })

  it('toggleTheme flips the theme, persists it, and updates the document attribute', async () => {
    localStorage.setItem('grid-theme', 'light')
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: false } as MediaQueryList))
    const { useThemeStore } = await import('./themeStore')

    useThemeStore.getState().toggleTheme()

    expect(useThemeStore.getState().theme).toBe('dark')
    expect(localStorage.getItem('grid-theme')).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('setTheme sets an explicit theme', async () => {
    const { useThemeStore } = await import('./themeStore')

    useThemeStore.getState().setTheme('dark')

    expect(useThemeStore.getState().theme).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
  })
})
