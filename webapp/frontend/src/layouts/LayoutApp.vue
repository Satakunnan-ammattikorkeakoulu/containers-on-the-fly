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
            <router-link to="/admin/audit-log" :class="{ 'nav-active': $route.path === '/admin/audit-log' }">Audit Log</router-link>
            <router-link to="/admin/analytics" :class="{ 'nav-active': $route.path === '/admin/analytics' }">Analytics</router-link>
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
                <v-list-item :to="'/admin/audit-log'"><v-list-item-title>Audit Log</v-list-item-title></v-list-item>
                <v-list-item :to="'/admin/analytics'"><v-list-item-title>Analytics</v-list-item-title></v-list-item>
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
      <div class="navbar-spacer"></div>

      <v-main>
        <v-container>
          <slot></slot>
        </v-container>
      </v-main>

      <footer v-if="legalEnabled" class="app-legal-footer">
        <a href="#" @click.prevent="openLegalModal('privacy-policy')">Privacy Policy</a>
        <span class="mx-2">|</span>
        <a href="#" @click.prevent="openLegalModal('terms-of-service')">Terms of Service</a>
      </footer>

      <!-- Legal Document Modal -->
      <v-dialog v-model="legalModal.visible" max-width="900" scrollable>
        <v-card>
          <v-card-title class="d-flex align-center">
            <span>{{ legalModal.title }}</span>
            <v-spacer></v-spacer>
            <v-btn icon variant="text" @click="legalModal.visible = false">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </v-card-title>
          <v-divider></v-divider>
          <v-card-text class="pa-6">
            <v-progress-linear v-if="legalModal.loading" indeterminate color="primary" class="mb-4"></v-progress-linear>
            <v-alert v-if="legalModal.error" type="warning" variant="outlined">{{ legalModal.errorMessage }}</v-alert>
            <div v-if="legalModal.renderedContent" class="legal-modal-content" v-html="legalModal.renderedContent"></div>
            <div v-if="!legalModal.loading && !legalModal.error && !legalModal.renderedContent" class="text-grey text-center pa-4">
              No content has been configured yet.
            </div>
          </v-card-text>
        </v-card>
      </v-dialog>

      <Snackbar></Snackbar>
    </v-app>
  </div>
</template>

<script>
  /**
   * Main authenticated layout. Provides a sticky top navigation bar with links to
   * user reservations and admin pages (inline on wide screens, dropdown on narrow),
   * a user account menu, and a global Snackbar. Redirects to logout if the user
   * session is missing.
   */
  import Snackbar from '/src/components/global/Snackbar.vue';
  import { useMainStore } from '@/store/store'
  import frontBgImg from '/src/assets/images/front_bg.png'
  import axios from 'axios'
  import { marked } from 'marked'
  import DOMPurify from 'dompurify'
  import { fillTemplate } from '/src/helpers/legalTemplates'

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
      legalModal: {
        visible: false,
        loading: false,
        title: '',
        renderedContent: '',
        error: false,
        errorMessage: ''
      }
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
      },
      /**
       * Open the legal document modal and fetch content from the API.
       * @param {string} type - Either 'privacy-policy' or 'terms-of-service'.
       */
      openLegalModal(type) {
        this.legalModal.visible = true
        this.legalModal.loading = true
        this.legalModal.error = false
        this.legalModal.renderedContent = ''
        this.legalModal.title = type === 'privacy-policy' ? 'Privacy Policy' : 'Terms of Service'

        const url = type === 'privacy-policy'
          ? this.$appSettings.APIServer.legal.get_privacy_policy
          : this.$appSettings.APIServer.legal.get_terms_of_service

        axios.get(url)
          .then((response) => {
            if (response.data && response.data.status) {
              const raw = response.data.data.content || ''
              const orgName = response.data.data.organizationName || ''
              const email = response.data.data.contactEmail || ''
              const lastUpdated = response.data.data.lastUpdated || ''
              if (raw) {
                const filled = fillTemplate(raw, orgName, email, lastUpdated)
                this.legalModal.renderedContent = DOMPurify.sanitize(marked.parse(filled))
              }
            } else {
              this.legalModal.error = true
              this.legalModal.errorMessage = response.data?.message || 'Could not load document.'
            }
          })
          .catch(() => {
            this.legalModal.error = true
            this.legalModal.errorMessage = 'Could not load document.'
          })
          .finally(() => {
            this.legalModal.loading = false
          })
      }
    },
    computed: {
      isInitializing() {
        return this.store.isInitializing
      },
      isLoggedIn() {
        return this.store.isLoggedIn || false
      },
      /** Checks both legacy single-role and multi-role arrays for admin access. */
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
      legalEnabled() {
        return this.store.legalEnabled
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
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background-color: #212121;
  box-shadow: 0 2px 4px -1px rgba(0, 0, 0, .2), 0 4px 5px 0 rgba(0, 0, 0, .14), 0 1px 10px 0 rgba(0, 0, 0, .12);
}

.navbar-spacer {
  height: 68px;
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

.app-legal-footer {
  text-align: center;
  margin-top: 80px;
  padding: 16px 0;
  font-size: 12px;
  opacity: 0.6;
  border-top: 1px solid rgba(0, 0, 0, 0.08);

  a {
    color: inherit;
    text-decoration: none;
    cursor: pointer;

    &:hover {
      text-decoration: underline;
    }
  }
}

.legal-modal-content {
  text-align: left;
  line-height: 1.7;

  :deep(h1) { font-size: 1.5rem; margin-top: 1.5rem; margin-bottom: 0.75rem; }
  :deep(h2) { font-size: 1.25rem; margin-top: 1.25rem; margin-bottom: 0.5rem; }
  :deep(h3) { font-size: 1.1rem; margin-top: 1rem; margin-bottom: 0.5rem; }
  :deep(p) { margin-bottom: 0.75rem; }
  :deep(ul), :deep(ol) { margin-bottom: 0.75rem; padding-left: 1.5rem; }
  :deep(li) { margin-bottom: 0.25rem; }
  :deep(table) { border-collapse: collapse; margin-bottom: 1rem; width: 100%; }
  :deep(th), :deep(td) { border: 1px solid rgba(255, 255, 255, 0.15); padding: 8px 12px; text-align: left; }
  :deep(th) { font-weight: 600; }
}
</style>
