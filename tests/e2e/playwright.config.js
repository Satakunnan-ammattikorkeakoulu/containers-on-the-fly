import { defineConfig } from '@playwright/test'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ADMIN_STATE = resolve(__dirname, '.auth/admin.json')
const USER_STATE = resolve(__dirname, '.auth/user.json')

export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  retries: 0,
  fullyParallel: true,
  use: {
    baseURL: 'http://localhost:8080',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },
  projects: [
    // Setup: login once, save session state (runs first, sequentially)
    {
      name: 'setup',
      testDir: '.',
      testMatch: /auth\.setup\.js/,
    },
    // Tests that need admin session
    {
      name: 'admin',
      use: { storageState: ADMIN_STATE },
      dependencies: ['setup'],
      testMatch: [/admin-management/, /auth\.spec/],
    },
    // Tests that need user session
    {
      name: 'user',
      use: { storageState: USER_STATE },
      dependencies: ['setup'],
      testMatch: [/reservation-flow/, /user-access/],
    },
    // Tests that need no auth (fresh browser)
    {
      name: 'noauth',
      use: { storageState: undefined },
      dependencies: ['setup'],
      testMatch: [/navigation-guards/],
    },
  ],
})
