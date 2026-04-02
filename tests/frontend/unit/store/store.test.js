import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMainStore } from '@/store/store.js'

describe('Main Store', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useMainStore()
  })

  // -----------------------------------------------------------------------
  // Getters
  // -----------------------------------------------------------------------

  describe('isLoggedIn', () => {
    it('returns false when no token', () => {
      expect(store.isLoggedIn).toBe(false)
    })

    it('returns true when token is set', () => {
      store.user.loginToken = 'some-token'
      expect(store.isLoggedIn).toBe(true)
    })
  })

  describe('appName', () => {
    it('returns default when not configured', () => {
      expect(store.appName).toBe('Containers on the Fly')
    })

    it('returns configured name', () => {
      store.appConfig.app.name = 'My App'
      expect(store.appName).toBe('My App')
    })
  })

  describe('reservation limit getters', () => {
    it('returns default limits', () => {
      expect(store.userMinDuration).toBe(1)
      expect(store.userMaxDuration).toBe(48)
      expect(store.userMaxActiveReservations).toBe(1)
    })

    it('returns updated limits', () => {
      store.user.reservationLimits = {
        minDuration: 2,
        maxDuration: 72,
        maxActiveReservations: 5,
      }
      expect(store.userMinDuration).toBe(2)
      expect(store.userMaxDuration).toBe(72)
      expect(store.userMaxActiveReservations).toBe(5)
    })
  })

  // -----------------------------------------------------------------------
  // Actions
  // -----------------------------------------------------------------------

  describe('user.name', () => {
    it('defaults to empty string', () => {
      expect(store.user.name).toBe('')
    })

    it('can be set directly', () => {
      store.user.name = 'Test User'
      expect(store.user.name).toBe('Test User')
    })
  })

  describe('logoutUser', () => {
    it('clears all user data', () => {
      store.user.loginToken = 'token'
      store.user.email = 'test@example.com'
      store.user.name = 'Test User'
      store.user.role = 'admin'
      store.user.roles = ['admin']

      store.logoutUser()

      expect(store.user.loginToken).toBe('')
      expect(store.user.email).toBe('')
      expect(store.user.name).toBe('')
      expect(store.user.role).toBe('')
      expect(store.user.roles).toEqual([])
      expect(store.user.loggedinAt).toBeNull()
    })

    it('removes user from localStorage', () => {
      localStorage.setItem('user', JSON.stringify({ loginToken: 'x' }))
      store.logoutUser()
      expect(localStorage.getItem('user')).toBeNull()
    })
  })

  describe('showMessage', () => {
    it('sets snackbar state', () => {
      store.showMessage({ text: 'Hello', color: 'green' })
      expect(store.snackbar.text).toBe('Hello')
      expect(store.snackbar.color).toBe('green')
      expect(store.snackbar.visible).toBe(true)
    })

    it('sets multiline for long text', () => {
      const longText = 'A'.repeat(51)
      store.showMessage({ text: longText })
      expect(store.snackbar.multiline).toBe(true)
    })

    it('short text is not multiline', () => {
      store.showMessage({ text: 'Short' })
      expect(store.snackbar.multiline).toBe(false)
    })

    it('uses primary color as default', () => {
      store.showMessage({ text: 'test' })
      expect(store.snackbar.color).toBe('primary')
    })
  })

  describe('closeMessage', () => {
    it('hides snackbar', () => {
      store.snackbar.visible = true
      store.closeMessage()
      expect(store.snackbar.visible).toBe(false)
    })
  })

  describe('setAppConfig', () => {
    it('merges config and sets loaded', () => {
      store.setAppConfig({ app: { name: 'Test App', timezone: 'UTC', contactEmail: '' } })
      expect(store.appConfig.app.name).toBe('Test App')
      expect(store.configLoaded).toBe(true)
      expect(store.configError).toBe(false)
    })
  })

  describe('setConfigError', () => {
    it('sets error state', () => {
      store.setConfigError('Connection failed')
      expect(store.configError).toBe(true)
      expect(store.configErrorMessage).toBe('Connection failed')
      expect(store.configLoaded).toBe(false)
    })
  })

  describe('clearConfigError', () => {
    it('resets error', () => {
      store.setConfigError('err')
      store.clearConfigError()
      expect(store.configError).toBe(false)
      expect(store.configErrorMessage).toBe('')
    })
  })
})
