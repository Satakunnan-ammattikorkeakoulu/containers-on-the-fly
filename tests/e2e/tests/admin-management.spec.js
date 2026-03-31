import { test, expect } from '@playwright/test'

test.describe('Admin Management', () => {

  test('admin can view users page', async ({ page }) => {
    // storageState already has admin session
    await page.goto('/admin/users')
    await expect(page).toHaveURL(/\/admin\/users/)
  })

  test('admin can view computers page', async ({ page }) => {
    await page.goto('/admin/computers')
    await expect(page).toHaveURL(/\/admin\/computers/)
  })

  test('admin can view containers page', async ({ page }) => {
    await page.goto('/admin/containers')
    await expect(page).toHaveURL(/\/admin\/containers/)
  })

  test('admin can view roles page', async ({ page }) => {
    await page.goto('/admin/roles')
    await expect(page).toHaveURL(/\/admin\/roles/)
  })

  test('admin can view general settings page', async ({ page }) => {
    await page.goto('/admin/general')
    await expect(page).toHaveURL(/\/admin\/general/)
  })
})
