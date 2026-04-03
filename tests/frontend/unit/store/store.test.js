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

  describe('isInitializing', () => {
    it('defaults to true', () => {
      expect(store.isInitializing).toBe(true)
    })

    it('reflects state change', () => {
      store.initializing = false
      expect(store.isInitializing).toBe(false)
    })
  })

  describe('hasConfigError', () => {
    it('defaults to false', () => {
      expect(store.hasConfigError).toBe(false)
    })

    it('returns true after setConfigError', () => {
      store.setConfigError('Oops')
      expect(store.hasConfigError).toBe(true)
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

  describe('appTimezone', () => {
    it('defaults to empty string', () => {
      expect(store.appTimezone).toBe('')
    })

    it('returns configured timezone', () => {
      store.appConfig.app.timezone = 'Europe/Helsinki'
      expect(store.appTimezone).toBe('Europe/Helsinki')
    })
  })

  describe('contactEmail', () => {
    it('defaults to empty string', () => {
      expect(store.contactEmail).toBe('')
    })

    it('returns configured email', () => {
      store.appConfig.app.contactEmail = 'admin@example.com'
      expect(store.contactEmail).toBe('admin@example.com')
    })
  })

  describe('instruction getters', () => {
    it('loginPageInfo returns configured value', () => {
      store.appConfig.instructions.login = 'Use your LDAP credentials'
      expect(store.loginPageInfo).toBe('Use your LDAP credentials')
    })

    it('reservationPageInstructions returns configured value', () => {
      store.appConfig.instructions.reservation = 'Pick a time slot'
      expect(store.reservationPageInstructions).toBe('Pick a time slot')
    })

    it('emailInstructions returns configured value', () => {
      store.appConfig.instructions.email = 'Check your inbox'
      expect(store.emailInstructions).toBe('Check your inbox')
    })

    it('usernameField returns configured label', () => {
      store.appConfig.instructions.usernameFieldLabel = 'Employee ID'
      expect(store.usernameField).toBe('Employee ID')
    })

    it('passwordField returns configured label', () => {
      store.appConfig.instructions.passwordFieldLabel = 'LDAP Password'
      expect(store.passwordField).toBe('LDAP Password')
    })
  })

  describe('userReservationLimits', () => {
    it('returns full limits object', () => {
      const limits = store.userReservationLimits
      expect(limits).toHaveProperty('minDuration')
      expect(limits).toHaveProperty('maxDuration')
      expect(limits).toHaveProperty('maxActiveReservations')
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

    it('accepts custom timeout', () => {
      store.showMessage({ text: 'quick', timeout: 2000 })
      expect(store.snackbar.timeout).toBe(2000)
    })

    it('accepts forced multiline', () => {
      store.showMessage({ text: 'short', multiline: true })
      expect(store.snackbar.multiline).toBe(true)
    })

    it('sets close button', () => {
      store.showMessage({ text: 'closeable', close: true })
      expect(store.snackbar.close).toBe(true)
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

    it('clears previous error state', () => {
      store.setConfigError('old error')
      store.setAppConfig({ app: { name: 'Fixed' } })
      expect(store.configError).toBe(false)
      expect(store.configErrorMessage).toBe('')
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

  describe('setUser', () => {
    it('calls callback with failure when no token', () => {
      const callback = vi.fn()
      store.setUser({ callback })
      expect(callback).toHaveBeenCalledWith(
        expect.objectContaining({ success: false })
      )
    })

    it('creates default callback when none provided', () => {
      // Should not throw when called without callback
      store.setUser({ loginToken: '' })
    })
  })

  describe('initialiseStore', () => {
    it('defaults initializing to true', () => {
      expect(store.initializing).toBe(true)
    })

    it('initializing can be set to false', () => {
      store.initializing = false
      expect(store.initializing).toBe(false)
    })
  })

})
