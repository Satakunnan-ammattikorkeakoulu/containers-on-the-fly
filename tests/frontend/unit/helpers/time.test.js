import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMainStore } from '@/store/store.js'
import { DisplayTime, TimestampToLocalTimeZone, RelativeTime, ServerNow } from '@/helpers/time.js'

describe('time helpers', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useMainStore()
    store.appConfig.app.timezone = 'UTC'
  })

  describe('DisplayTime', () => {
    it('formats a UTC timestamp correctly', () => {
      const result = DisplayTime('2024-01-15T10:30:00Z')
      expect(result).toBe('15.01.2024 10:30')
    })

    it('appends Z to timestamp without it', () => {
      const result = DisplayTime('2024-06-01T14:00:00')
      expect(result).toBe('01.06.2024 14:00')
    })

    it('respects timezone setting', () => {
      store.appConfig.app.timezone = 'Europe/Helsinki'  // UTC+2 / UTC+3
      const result = DisplayTime('2024-01-15T10:00:00Z')
      // Helsinki is UTC+2 in January
      expect(result).toBe('15.01.2024 12:00')
    })
  })

  describe('TimestampToLocalTimeZone', () => {
    it('returns a valid ISO string', () => {
      const result = TimestampToLocalTimeZone('2024-01-15T10:30:00Z')
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T/)
    })

    it('appends Z to timestamp without it', () => {
      // Should not throw
      const result = TimestampToLocalTimeZone('2024-01-15T10:30:00')
      expect(typeof result).toBe('string')
    })
  })

  describe('ServerNow and RelativeTime', () => {
    beforeEach(() => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2024-01-15T10:00:00Z'))
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('ServerNow equals the client time when there is no offset', () => {
      expect(ServerNow().toISOString()).toBe('2024-01-15T10:00:00.000Z')
    })

    it('ServerNow applies the measured clock offset', () => {
      // Client clock is two hours ahead of the server
      store.clockOffsetMs = -2 * 60 * 60 * 1000
      expect(ServerNow().toISOString()).toBe('2024-01-15T08:00:00.000Z')
    })

    it('RelativeTime is relative to the client time when there is no offset', () => {
      expect(RelativeTime('2024-01-15T09:57:00Z')).toBe('3 minutes ago')
    })

    it('RelativeTime is relative to the server time', () => {
      // Client clock is two hours ahead, so 08:00 is "now" for the server
      store.clockOffsetMs = -2 * 60 * 60 * 1000
      expect(RelativeTime('2024-01-15T07:57:00Z')).toBe('3 minutes ago')
      expect(RelativeTime('2024-01-15T10:00:00Z')).toBe('in 2 hours')
    })
  })
})
