import { test, expect } from '@playwright/test'

test.describe('User Access', () => {

  test('non-admin redirected from admin pages', async ({ page }) => {
    // storageState already has user session
    await page.goto('/admin/users')
    await expect(page).toHaveURL(/\/user\/reservations/)
  })
})
