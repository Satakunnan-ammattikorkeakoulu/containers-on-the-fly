import { describe, it, expect } from 'vitest'
import createUrls from '@/AppUrls.js'

describe('createUrls', () => {
  const base = 'http://localhost/api/'
  const urls = createUrls(base)

  it('creates user URLs', () => {
    expect(urls.user.login).toBe(base + 'user/login')
    expect(urls.user.check_token).toBe(base + 'user/check_token')
  })

  it('creates reservation URLs', () => {
    expect(urls.reservation.get_available_hardware).toBe(base + 'reservation/get_available_hardware')
    expect(urls.reservation.create_reservation).toBe(base + 'reservation/create_reservation')
    expect(urls.reservation.get_own_reservations).toBe(base + 'reservation/get_own_reservations')
    expect(urls.reservation.cancel_reservation).toBe(base + 'reservation/cancel_reservation')
    expect(urls.reservation.extend_reservation).toBe(base + 'reservation/extend_reservation')
    expect(urls.reservation.restart_container).toBe(base + 'reservation/restart_container')
  })

  it('creates admin URLs', () => {
    expect(urls.admin.get_users).toBe(base + 'admin/users')
    expect(urls.admin.get_computers).toBe(base + 'admin/computers')
    expect(urls.admin.get_containers).toBe(base + 'admin/containers')
    expect(urls.admin.get_roles).toBe(base + 'admin/roles')
    expect(urls.admin.save_role).toBe(base + 'admin/save_role')
    expect(urls.admin.remove_role).toBe(base + 'admin/remove_role')
    expect(urls.admin.get_general_settings).toBe(base + 'admin/general-settings')
  })

  it('creates app URLs', () => {
    expect(urls.app.get_config).toBe(base + 'app/config')
  })

  it('all URLs start with the base address', () => {
    const allUrls = [
      ...Object.values(urls.user),
      ...Object.values(urls.reservation),
      ...Object.values(urls.admin),
      ...Object.values(urls.app),
    ]
    for (const url of allUrls) {
      expect(url.startsWith(base)).toBe(true)
    }
  })
})
