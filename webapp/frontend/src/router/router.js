import Vue from 'vue'
import VueRouter from 'vue-router'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    name: 'login',
    component: () => import(/* webpackChunkName: "login" */ '../views/ViewLogin.vue')
  },
  {
    path: '/user/logout',
    name: 'user/logout',
    component: () => import(/* webpackChunkName: "userlogout" */ '../views/user/ViewUserLogout.vue')
  },
  {
    path: '/user/reservations',
    name: 'user/reservations',
    component: () => import(/* webpackChunkName: "userreservations" */ '../views/user/ViewUserReservations.vue')
  },
  {
    path: '/user/reserve',
    name: 'user/reserve',
    component: () => import(/* webpackChunkName: "userreserve" */ '../views/user/ViewUserReserve.vue')
  },
  {
    path: '/admin/general',
    name: 'admin/general',
    component: () => import(/* webpackChunkName: "admingeneral" */ '../views/admin/ViewAdminGeneral.vue')
  },
  {
    path: '/admin/reservations',
    name: 'admin/reservations',
    component: () => import(/* webpackChunkName: "adminreservations" */ '../views/admin/ViewAdminReservations.vue')
  },
  {
    path: '/admin/users',
    name: 'admin/users',
    component: () => import(/* webpackChunkName: "adminusers" */ '../views/admin/ViewAdminUsers.vue')
  },
  {
    path: '/admin/hardware',
    name: 'admin/hardware',
    component: () => import(/* webpackChunkName: "adminhardware" */ '../views/admin/ViewAdminHardware.vue')
  },
  {
    path: '/admin/containers',
    name: 'admin/containers',
    component: () => import(/* webpackChunkName: "admincontainers" */ '../views/admin/ViewAdminContainers.vue')
  },
  {
    path: '/admin/computers',
    name: 'admin/computers',
    component: () => import(/* webpackChunkName: "admincomputers" */ '../views/admin/ViewAdminComputers.vue')
  },
  {
    path: '/admin/roles',
    name: 'admin/roles',
    component: () => import(/* webpackChunkName: "adminroles" */ '../views/admin/ViewAdminRoles.vue')
  },
  {
    // path: "*",
    path: "/:catchAll(.*)",
    name: "NotFound",
    component: () => import(/* webpackChunkName: "pagenotfound" */ '../views/ViewPageNotFound.vue')
  },
]

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes
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
