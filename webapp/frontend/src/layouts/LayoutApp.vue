<template>
  <div v-if="!isInitializing">
    <v-app v-if="isLoggedIn">
      <div class="navbar" :class="{ 'navbar-compact': scrolled }">
        <v-container class="navbar-inner">
          <div class="app-logo" @click="reservations">
            <img :src="frontBgImg" class="app-logo-img" alt="Logo" />
          </div>
          <a @click="reservations" :class="{ 'nav-active': $route.path.startsWith('/user/reserv') }">Reservations</a>
          <!-- Admin links: inline on wide screens -->
          <div class="admin-block admin-inline" v-if="isAdmin">
            <p class="admin-text">Admin</p>
            <router-link to="/admin/general" :class="{ 'nav-active': $route.path === '/admin/general' }">General</router-link>
            <router-link to="/admin/reservations" :class="{ 'nav-active': $route.path === '/admin/reservations' }">Reservations</router-link>
            <router-link to="/admin/users" :class="{ 'nav-active': $route.path === '/admin/users' }">Users</router-link>
            <router-link to="/admin/roles" :class="{ 'nav-active': $route.path === '/admin/roles' }">Roles</router-link>
            <router-link to="/admin/computers" :class="{ 'nav-active': $route.path === '/admin/computers' }">Computers</router-link>
            <router-link to="/admin/containers" :class="{ 'nav-active': $route.path === '/admin/containers' }">Containers</router-link>
          </div>
          <!-- Admin links: dropdown on narrow screens -->
          <div class="admin-dropdown" v-if="isAdmin">
            <v-menu offset-y>
              <template v-slot:activator="{ props }">
                <span class="admin-dropdown-trigger" v-bind="props">Admin <v-icon size="small">mdi-chevron-down</v-icon></span>
              </template>
              <v-list>
                <v-list-item :to="'/admin/general'"><v-list-item-title>General</v-list-item-title></v-list-item>
                <v-list-item :to="'/admin/reservations'"><v-list-item-title>Reservations</v-list-item-title></v-list-item>
                <v-list-item :to="'/admin/users'"><v-list-item-title>Users</v-list-item-title></v-list-item>
                <v-list-item :to="'/admin/roles'"><v-list-item-title>Roles</v-list-item-title></v-list-item>
                <v-list-item :to="'/admin/computers'"><v-list-item-title>Computers</v-list-item-title></v-list-item>
                <v-list-item :to="'/admin/containers'"><v-list-item-title>Containers</v-list-item-title></v-list-item>
              </v-list>
            </v-menu>
          </div>
          <div class="user-info-container" v-if="isLoggedIn == true">
            <v-menu offset-y>
              <template v-slot:activator="{ props }">
                <v-icon
                  v-bind="props"
                  class="user-menu-icon"
                  size="28"
                >mdi-account-circle</v-icon>
              </template>
              <v-list>
                <v-list-item :disabled="true" class="user-info-header">
                  <v-list-item-title style="font-size: 12px; opacity: 0.7;">Logged in as <strong>{{ userEmail }}</strong></v-list-item-title>
                  <v-list-item-subtitle v-if="userRoles.length > 0" style="font-size: 11px; margin-top: 4px;">
                    Roles: {{ userRoles.join(', ') }}
                  </v-list-item-subtitle>
                </v-list-item>
                <v-divider></v-divider>
                <v-list-item @click="profile">
                  <v-list-item-title>Profile</v-list-item-title>
                </v-list-item>
                <v-list-item @click="logout">
                  <v-list-item-title>Logout</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </div>
        </v-container>
      </div>

      <v-main>
        <v-container>
          <slot></slot>
        </v-container>
      </v-main>

      <Snackbar></Snackbar>
    </v-app>
  </div>
</template>

<script>
  import Snackbar from '/src/components/global/Snackbar.vue';
  import { useMainStore } from '@/store/store'
  import frontBgImg from '/src/assets/images/front_bg.png'

  export default {
    name: 'LayoutApp',
    setup() {
      const store = useMainStore()
      return { store }
    },
    components: {
      Snackbar,
    },
    data: () => ({
      show: true,
      frontBgImg,
      scrolled: false,
    }),
    mounted() {
      if (!this.isInitializing) {
        if (!this.isLoggedIn) {
          console.log("User is not logged in and trying to access logged-in users page")
          this.$router.push("/user/logout")
        }
      }
      this.handleScroll = () => {
        this.scrolled = window.scrollY > 20
      }
      window.addEventListener('scroll', this.handleScroll)
    },
    beforeUnmount() {
      window.removeEventListener('scroll', this.handleScroll)
    },
    methods: {
      logout() {
        this.$router.push("/user/logout")
      },
      reservations() {
        this.$router.push("/user/reservations")
      },
      profile() {
        this.$router.push("/user/profile")
      }
    },
    computed: {
      isInitializing() {
        return this.store.isInitializing
      },
      isLoggedIn() {
        return this.store.isLoggedIn || false
      },
      isAdmin() {
        let currentUser = this.store.user
        if (!currentUser) return false

        if (currentUser.role == "admin") return true
        if (currentUser.roles && currentUser.roles.includes("admin")) return true
        return false
      },
      userEmail() {
        if (!this.store.user) return ""
        return this.store.user.email || ""
      },
      userRoles() {
        if (!this.store.user) return []
        return this.store.user.roles || []
      },
      appName() {
        return this.store.appName
      },
    },
    beforeRouteUpdate(to, from, next) {
      this.show = false
      next()
    },
    watch: {
      $route (to, from) {
        this.show = true
        console.log(to, from)
      },
      isInitializing() {
        //console.log("new val: " + newVal)
      },
    }
  }
</script>

<style scoped lang="scss">
.navbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  background-color: #212121;
  box-shadow: 0 2px 4px -1px rgba(0, 0, 0, .2), 0 4px 5px 0 rgba(0, 0, 0, .14), 0 1px 10px 0 rgba(0, 0, 0, .12);
}

.navbar-inner {
  display: flex !important;
  align-items: center;
  height: 68px;
  transition: height 0.25s ease;
  flex-wrap: nowrap;
}

.app-logo-img {
  transition: height 0.25s ease;
}

.navbar a {
  color: white !important;
  margin: 0 15px !important;
  transition: 0.2s all ease;
  text-decoration: none;
  font-size: 15px;
}

.navbar a:hover {
  color: #2096f3 !important;
}

.navbar-compact .navbar-inner {
  height: 48px;
}

.navbar-compact a {
  font-size: 14px !important;
}

.navbar-compact .app-logo-img {
  height: 26px;
}

.navbar-compact .admin-text {
  font-size: 13px !important;
}

.user-info-container {
  margin-left: auto;
  display: flex;
  align-items: center;
}

.user-menu-icon {
  color: rgba(255, 255, 255, 0.85);
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: white;
  }
}

.user-info-header {
  padding: 12px 20px !important;
  margin-bottom: 4px;
}

.admin-block {
  margin-left: 20px;
}

.admin-block p {
  margin: 0px;
  color: gray;
  font-size: 15px;
  margin-right: 5px;
}

.admin-block > a {
  text-decoration: none;
  font-size: 15px;
}

.admin-block > * {
  display: inline-block;
}

.nav-active {
  font-weight: bold !important;
}

.app-logo {
  display: flex;
  align-items: center;
  cursor: pointer;
  margin-right: 10px;
  white-space: nowrap;
}

.app-logo-img {
  height: 32px;
  object-fit: contain;
}

.admin-dropdown {
  display: none;
  margin-left: 20px;
}

.admin-dropdown-trigger {
  color: white;
  cursor: pointer;
  font-size: 15px;
  display: flex;
  align-items: center;
}

@media (max-width: 1150px) {
  .admin-inline {
    display: none !important;
  }

  .admin-dropdown {
    display: block;
  }
}
</style>
