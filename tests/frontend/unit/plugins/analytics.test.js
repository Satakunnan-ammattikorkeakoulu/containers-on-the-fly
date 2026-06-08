/**
 * Tests for plugins/analytics.js
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { initAnalytics, identifyUser, clearUserIdentity } from '@/plugins/analytics.js'

describe('initAnalytics', () => {
  let appendChildSpy

  beforeEach(() => {
    // Clear any scripts from prior tests
    document.head.innerHTML = ''
    appendChildSpy = vi.spyOn(document.head, 'appendChild').mockImplementation(() => {})
    delete window.rybbit
    delete window.gtag
    delete window.dataLayer
  })

  afterEach(() => {
    appendChildSpy.mockRestore()
  })

  it('does nothing when config is null', () => {
    initAnalytics(null)
    expect(appendChildSpy).not.toHaveBeenCalled()
  })

  it('does nothing when config is empty', () => {
    initAnalytics({})
    expect(appendChildSpy).not.toHaveBeenCalled()
  })

  it('does nothing when only rybbitUrl is set without rybbitSiteId', () => {
    initAnalytics({ rybbitUrl: 'https://analytics.example.com' })
    expect(appendChildSpy).not.toHaveBeenCalled()
  })

  it('injects rybbit script when both rybbitUrl and rybbitSiteId are set', () => {
    initAnalytics({
      rybbitUrl: 'https://analytics.example.com',
      rybbitSiteId: '42',
    })
    expect(appendChildSpy).toHaveBeenCalledTimes(1)
    const script = appendChildSpy.mock.calls[0][0]
    expect(script.src).toContain('analytics.example.com/api/script.js')
    expect(script.getAttribute('data-site-id')).toBe('42')
  })

  it('rejects unsafe rybbit URL', () => {
    initAnalytics({
      rybbitUrl: 'javascript:alert(1)',
      rybbitSiteId: '42',
    })
    expect(appendChildSpy).not.toHaveBeenCalled()
  })

  it('injects GA script when googleAnalyticsId matches format', () => {
    initAnalytics({ googleAnalyticsId: 'G-ABCDEF1234' })
    expect(appendChildSpy).toHaveBeenCalledTimes(1)
    const script = appendChildSpy.mock.calls[0][0]
    expect(script.src).toContain('googletagmanager.com/gtag/js?id=G-ABCDEF1234')
  })

  it('skips GA when ID does not match expected format', () => {
    initAnalytics({ googleAnalyticsId: 'UA-123456' })
    expect(appendChildSpy).not.toHaveBeenCalled()
  })
})

describe('identifyUser', () => {
  beforeEach(() => {
    delete window.rybbit
    delete window.gtag
    delete window.dataLayer
    // Re-init analytics config so identifyUser has context
    document.head.innerHTML = ''
    vi.spyOn(document.head, 'appendChild').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('does nothing when user is null', () => {
    identifyUser(null)
    // No error thrown
  })

  it('does nothing when user has no email', () => {
    identifyUser({ name: 'Test' })
    // No error thrown
  })

  it('calls rybbit.identify when rybbit is available', () => {
    window.rybbit = { identify: vi.fn(), clearUserId: vi.fn() }
    initAnalytics({ rybbitUrl: 'https://r.example.com', rybbitSiteId: '1' })

    identifyUser({ email: 'test@example.com', name: 'Test User' })
    expect(window.rybbit.identify).toHaveBeenCalledWith(
      'test@example.com',
      { name: 'Test User', email: 'test@example.com' }
    )
  })

  it('calls gtag with hashed user ID', async () => {
    window.gtag = vi.fn()
    initAnalytics({ googleAnalyticsId: 'G-TEST123' })

    identifyUser({ email: 'test@example.com', name: 'Test' })

    // hashString is async, so wait for promise resolution
    await new Promise(resolve => setTimeout(resolve, 10))

    expect(window.gtag).toHaveBeenCalledWith(
      'config',
      'G-TEST123',
      expect.objectContaining({ user_id: expect.any(String) })
    )
    // Verify the user_id is a hash, not the raw email
    const userIdArg = window.gtag.mock.calls.find(
      c => c[0] === 'config' && c[2]?.user_id
    )
    expect(userIdArg[2].user_id).not.toBe('test@example.com')
  })

  it('does nothing when no analytics globals exist', () => {
    initAnalytics({ rybbitUrl: 'https://r.example.com', rybbitSiteId: '1' })
    // window.rybbit is not set
    identifyUser({ email: 'test@example.com', name: 'Test' })
    // No error thrown
  })
})

describe('clearUserIdentity', () => {
  beforeEach(() => {
    delete window.rybbit
    delete window.gtag
    delete window.dataLayer
    document.head.innerHTML = ''
    vi.spyOn(document.head, 'appendChild').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('calls rybbit.clearUserId when rybbit is available', () => {
    window.rybbit = { identify: vi.fn(), clearUserId: vi.fn() }
    clearUserIdentity()
    expect(window.rybbit.clearUserId).toHaveBeenCalled()
  })

  it('calls gtag with null user_id when GA is active', () => {
    window.gtag = vi.fn()
    initAnalytics({ googleAnalyticsId: 'G-TEST123' })

    clearUserIdentity()
    expect(window.gtag).toHaveBeenCalledWith(
      'config',
      'G-TEST123',
      { user_id: null }
    )
  })

  it('does nothing when no analytics globals exist', () => {
    clearUserIdentity()
    // No error thrown
  })
})
