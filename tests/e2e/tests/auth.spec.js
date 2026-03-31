import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {

  test('admin session is valid after setup', async ({ page }) => {
    // storageState already has admin session from setup project
    await page.goto('/user/reservations')
    await expect(page).toHaveURL(/\/user\/reservations/)
    // Admin should see admin navigation
    await expect(page.locator('text=General')).toBeVisible()
  })

  test('admin session persists across page reload', async ({ page }) => {
    await page.goto('/user/reservations')
    await page.reload()
    await expect(page).toHaveURL(/\/user\/reservations/)
  })

  test('login with invalid credentials shows error', async ({ browser }) => {
    // Use a fresh context without storageState so we get the login page
    const context = await browser.newContext({ storageState: undefined })
    const page = await context.newPage()

    await page.goto('/')
    await page.locator('input[type="text"]').fill('wrong@foo.com')
    await page.locator('input[type="password"]').fill('wrong')
    await page.locator('button:has-text("Login")').click()
    // Should stay on login page
    await expect(page).toHaveURL('/')
    await context.close()
  })

  test('logout redirects to login page', async ({ page }) => {
    await page.goto('/user/logout')
    await expect(page).toHaveURL('/')
  })
})
