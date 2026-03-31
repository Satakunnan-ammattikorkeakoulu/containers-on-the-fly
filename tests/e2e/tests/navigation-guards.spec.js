import { test, expect } from '@playwright/test'

test.describe('Navigation Guards', () => {

  test('unauthenticated user redirected from protected routes', async ({ page }) => {
    await page.goto('/user/reservations')
    await expect(page).toHaveURL('/')
  })

  test('unknown route shows 404 page', async ({ page }) => {
    await page.goto('/nonexistent-route')
    await expect(page.locator('text=404').or(page.locator('text=Not Found'))).toBeVisible()
  })
})
