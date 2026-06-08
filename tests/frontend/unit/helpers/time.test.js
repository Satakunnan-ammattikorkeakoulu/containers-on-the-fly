import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMainStore } from '@/store/store.js'
import { DisplayTime, TimestampToLocalTimeZone } from '@/helpers/time.js'

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
})
