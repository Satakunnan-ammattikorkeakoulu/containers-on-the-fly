/**
 * Vue Router configuration and navigation guards.
 * Defines all application routes with lazy-loaded view components and
 * enforces authentication/authorisation via `beforeEach` guard.
 *
 * Route meta flags:
 *  - `requiresAuth` {boolean} - Redirect unauthenticated users to login.
 *  - `requiresAdmin` {boolean} - Restrict access to admin-role users.
 * @module router
 */

import { createRouter, createWebHistory } from 'vue-router'
import { useMainStore } from '../store/store'

/** @type {import('vue-router').RouteRecordRaw[]} */
const routes = [
  {
    path: '/',
    name: 'login',
    component: () => import('../views/ViewLogin.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/user/logout',
    name: 'user/logout',
    component: () => import('../views/user/ViewUserLogout.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/user/reservations',
    name: 'user/reservations',
    component: () => import('../views/user/ViewUserReservations.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/user/reserve',
    name: 'user/reserve',
    component: () => import('../views/user/ViewUserReserve.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/user/profile',
    name: 'user/profile',
    component: () => import('../views/user/ViewUserProfile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/general',
    name: 'admin/general',
    component: () => import('../views/admin/ViewAdminGeneral.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/reservations',
    name: 'admin/reservations',
    component: () => import('../views/admin/ViewAdminReservations.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/users',
    name: 'admin/users',
    component: () => import('../views/admin/ViewAdminUsers.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/hardware',
    name: 'admin/hardware',
    component: () => import('../views/admin/ViewAdminHardware.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/containers',
    name: 'admin/containers',
    component: () => import('../views/admin/ViewAdminContainers.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/computers',
    name: 'admin/computers',
    component: () => import('../views/admin/ViewAdminComputers.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/roles',
    name: 'admin/roles',
    component: () => import('../views/admin/ViewAdminRoles.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: "/:catchAll(.*)",
    name: "NotFound",
    component: () => import('../views/ViewPageNotFound.vue'),
    meta: { requiresAuth: false }
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

/**
 * Wait until the Pinia store finishes its async initialisation.
 * Called at the start of the navigation guard so that auth state is
 * available before any route-level checks run.
 * @param {Object} store - The main Pinia store instance.
 * @returns {Promise<void>} Resolves once `store.initializing` is false.
 */
function waitForStoreInit(store) {
  return new Promise((resolve) => {
    if (!store.initializing) {
      resolve()
    } else {
      const checkInit = setInterval(() => {
        if (!store.initializing) {
          clearInterval(checkInit)
          resolve()
        }
      }, 50)
    }
  })
}

/**
 * Global navigation guard.
 * - Waits for store initialisation before evaluating auth state.
 * - Redirects unauthenticated users away from protected routes.
 * - Redirects non-admin users away from admin routes.
 * - Redirects already-authenticated users from the login page to the user area.
 */
router.beforeEach(async (to, from) => {
  const store = useMainStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin)

  // Wait for store initialization to complete before checking authentication
  await waitForStoreInit(store)

  const isLoggedIn = store.isLoggedIn
  const user = store.user
  const isAdmin = user && (user.role === 'admin' || (user.roles && user.roles.includes('admin')))

  // If route requires authentication and user is not logged in
  if (requiresAuth && !isLoggedIn) {
    return { path: '/' }
  }

  // If route requires admin privileges and user is not admin
  if (requiresAdmin && (!isLoggedIn || !isAdmin)) {
    if (isLoggedIn) {
      return { path: '/user/reservations' }
    } else {
      return { path: '/' }
    }
  }

  // If user is logged in and trying to access login page, redirect to user area
  if (to.path === '/' && isLoggedIn) {
    return { path: '/user/reservations' }
  }
})

export default router
