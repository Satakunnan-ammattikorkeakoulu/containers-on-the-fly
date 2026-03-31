/**
 * Vitest global setup — runs before every test file.
 *
 * - Mocks axios so no real HTTP calls are made
 * - Provides a localStorage stub for jsdom
 */

import { vi } from 'vitest'

// Mock axios globally
vi.mock('axios', () => {
  return {
    default: {
      get: vi.fn(() => Promise.resolve({ data: {} })),
      post: vi.fn(() => Promise.resolve({ data: {} })),
      put: vi.fn(() => Promise.resolve({ data: {} })),
      delete: vi.fn(() => Promise.resolve({ data: {} })),
      create: vi.fn(function () { return this }),
      interceptors: {
        request: { use: vi.fn(), eject: vi.fn() },
        response: { use: vi.fn(), eject: vi.fn() },
      },
    },
  }
})
