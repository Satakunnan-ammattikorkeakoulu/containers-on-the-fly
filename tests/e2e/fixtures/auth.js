/**
 * Shared auth helpers for Playwright E2E tests.
 *
 * Reads credentials from tests/.test_credentials.json (created by setup_test_users.py).
 */

import { readFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const credentialsPath = resolve(__dirname, '../../.test_credentials.json')

let _credentials = null

function getCredentials() {
  if (!_credentials) {
    try {
      _credentials = JSON.parse(readFileSync(credentialsPath, 'utf-8'))
    } catch (e) {
      throw new Error(
        `Cannot read test credentials at ${credentialsPath}. ` +
        `Run "make test-e2e-setup" or the setup script first.\n` + e.message
      )
    }
  }
  return _credentials
}

/**
 * Login as the temporary admin account and wait for redirect.
 */
export async function loginAsAdmin(page) {
  const creds = getCredentials()
  await page.goto('/')
  await page.locator('input[type="text"]').fill(creds.admin_email)
  await page.locator('input[type="password"]').fill(creds.admin_password)
  await page.locator('button:has-text("Login")').click()
  await page.waitForURL('**/user/reservations', { timeout: 15000 })
}

/**
 * Login as the temporary normal user and wait for redirect.
 */
export async function loginAsUser(page) {
  const creds = getCredentials()
  await page.goto('/')
  await page.locator('input[type="text"]').fill(creds.user_email)
  await page.locator('input[type="password"]').fill(creds.user_password)
  await page.locator('button:has-text("Login")').click()
  await page.waitForURL('**/user/reservations', { timeout: 15000 })
}
