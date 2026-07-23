import { defineConfig, devices } from '@playwright/test'

// Runs against the real compose stack (ARCHITECTURE §9) — `make dev` must
// already be up. No webServer entry here on purpose: the frontend, API, and
// Postgres all need to be the real containers, not a Vite-only preview.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: process.env.GRID_E2E_BASE_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
