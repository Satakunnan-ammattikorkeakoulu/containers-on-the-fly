/**
 * Playwright auth setup — runs once before all test files.
 *
 * Logs in as admin and user, saves browser storage state so that
 * test files can reuse the sessions without hitting the login endpoint.
 * This avoids the race condition where concurrent logins overwrite
 * each other's tokens (the backend stores one token per user).
 */

import { test as setup, expect } from '@playwright/test'
import { readFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const credentialsPath = resolve(__dirname, '../.test_credentials.json')
const creds = JSON.parse(readFileSync(credentialsPath, 'utf-8'))

const ADMIN_STATE = resolve(__dirname, '.auth/admin.json')
const USER_STATE = resolve(__dirname, '.auth/user.json')

setup('authenticate as admin', async ({ page }) => {
  await page.goto('/')
  await page.locator('input[type="text"]').fill(creds.admin_email)
  await page.locator('input[type="password"]').fill(creds.admin_password)
  await page.locator('button:has-text("Login")').click()
  await page.waitForURL('**/user/reservations', { timeout: 15000 })
  await page.context().storageState({ path: ADMIN_STATE })
})

setup('authenticate as user', async ({ page }) => {
  await page.goto('/')
  await page.locator('input[type="text"]').fill(creds.user_email)
  await page.locator('input[type="password"]').fill(creds.user_password)
  await page.locator('button:has-text("Login")').click()
  await page.waitForURL('**/user/reservations', { timeout: 15000 })
  await page.context().storageState({ path: USER_STATE })
})
