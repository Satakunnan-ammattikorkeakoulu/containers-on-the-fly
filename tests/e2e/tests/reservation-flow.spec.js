import { test, expect } from '@playwright/test'

test.describe('Reservation Flow', () => {

  test('user can view own reservations page', async ({ page }) => {
    // storageState already has user session from setup project
    await page.goto('/user/reservations')
    await expect(page.getByRole('heading', { name: 'Your Reservations' })).toBeVisible()
  })

  test('user can navigate to reserve page', async ({ page }) => {
    await page.goto('/user/reservations')
    await page.click('text=Reservations')
    await expect(page).toHaveURL(/\/user\/reservations/)
  })

  test('reservation page shows status filters', async ({ page }) => {
    await page.goto('/user/reservations')
    await expect(page.locator('text=All').first()).toBeVisible()
  })
})
