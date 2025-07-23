import Vue from 'vue'
import VueRouter from 'vue-router'
import { store } from '../store/store'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    name: 'login',
    component: () => import(/* webpackChunkName: "login" */ '../views/ViewLogin.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/user/logout',
    name: 'user/logout',
    component: () => import(/* webpackChunkName: "userlogout" */ '../views/user/ViewUserLogout.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/user/reservations',
    name: 'user/reservations',
    component: () => import(/* webpackChunkName: "userreservations" */ '../views/user/ViewUserReservations.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/user/reserve',
    name: 'user/reserve',
    component: () => import(/* webpackChunkName: "userreserve" */ '../views/user/ViewUserReserve.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/general',
    name: 'admin/general',
    component: () => import(/* webpackChunkName: "admingeneral" */ '../views/admin/ViewAdminGeneral.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/reservations',
    name: 'admin/reservations',
    component: () => import(/* webpackChunkName: "adminreservations" */ '../views/admin/ViewAdminReservations.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/users',
    name: 'admin/users',
    component: () => import(/* webpackChunkName: "adminusers" */ '../views/admin/ViewAdminUsers.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/hardware',
    name: 'admin/hardware',
    component: () => import(/* webpackChunkName: "adminhardware" */ '../views/admin/ViewAdminHardware.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/containers',
    name: 'admin/containers',
    component: () => import(/* webpackChunkName: "admincontainers" */ '../views/admin/ViewAdminContainers.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/computers',
    name: 'admin/computers',
    component: () => import(/* webpackChunkName: "admincomputers" */ '../views/admin/ViewAdminComputers.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/roles',
    name: 'admin/roles',
    component: () => import(/* webpackChunkName: "adminroles" */ '../views/admin/ViewAdminRoles.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    // path: "*",
    path: "/:catchAll(.*)",
    name: "NotFound",
    component: () => import(/* webpackChunkName: "pagenotfound" */ '../views/ViewPageNotFound.vue'),
    meta: { requiresAuth: false }
  },
]

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes
})

// Helper function to wait for store initialization
function waitForStoreInit() {
  return new Promise((resolve) => {
    if (!store.getters.isInitializing) {
      resolve()
    } else {
      const unwatch = store.watch(
        state => state.initializing,
        (isInitializing) => {
          if (!isInitializing) {
            unwatch()
            resolve()
          }
        }
      )
    }
  })
}

// Navigation guards for authentication
router.beforeEach(async (to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin)
  
  // Wait for store initialization to complete before checking authentication
  await waitForStoreInit()
  
  const isLoggedIn = store.getters.isLoggedIn
  const user = store.getters.user
  const isAdmin = user && user.role === 'admin'

  // If route requires authentication and user is not logged in
  if (requiresAuth && !isLoggedIn) {
    // Redirect to login page
    next({ path: '/' })
    return
  }

  // If route requires admin privileges and user is not admin
  if (requiresAdmin && (!isLoggedIn || !isAdmin)) {
    // Redirect to user reservations if logged in, otherwise to login
    if (isLoggedIn) {
      next({ path: '/user/reservations' })
    } else {
      next({ path: '/' })
    }
    return
  }

  // If user is logged in and trying to access login page, redirect to user area
  if (to.path === '/' && isLoggedIn) {
    next({ path: '/user/reservations' })
    return
  }

  // Allow navigation
  next()
})

// Silence all errors happening when navigating between pages.
// This is mostly used to silence the annoying "NavigationDuplicated" error happening if you try to
// navigate to the same page.
const originalPush = VueRouter.prototype.push
VueRouter.prototype.push = function push(location, onResolve, onReject) {
  if (onResolve || onReject) return originalPush.call(this, location, onResolve, onReject)
  return originalPush.call(this, location).catch(err => err)
}

export default router
