import '@testing-library/jest-dom/vitest'

// jsdom doesn't implement scrollTo; TanStack Router's scroll restoration calls it
// on every navigation.
window.scrollTo = () => {}

// jsdom doesn't implement matchMedia; themeStore reads it at module init time
// (before any per-test vi.stubGlobal call runs), so every test needs a default.
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList
}
