<template>
  <div v-if="!isInitializing">
    <v-app v-if="isLoggedIn">
      <v-app-bar app elevation="4">
        <a @click="reservations">Reservations</a>
        <div class="admin-block" v-if="isAdmin">
          <p class="admin-text">Admin</p>
          <a href="/admin/general">General</a>
          <a href="/admin/reservations">Reservations</a>
          <a href="/admin/users">Users</a>
          <a href="/admin/roles">Roles</a>
          <a href="/admin/computers">Computers</a>
          <a href="/admin/containers">Containers</a>
        </div>
        <div class="user-info-container" v-if="isLoggedIn == true">
          <v-menu offset-y open-on-hover>
            <template v-slot:activator="{ on, attrs }">
              <span 
                class="user-email-link"
                v-bind="attrs"
                v-on="on"
              >
                {{userEmail}}
              </span>
            </template>
            <v-list>
              <v-list-item @click="profile">
                <v-list-item-title>Profile</v-list-item-title>
              </v-list-item>
              <v-list-item @click="logout">
                <v-list-item-title>Logout</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
          <v-tooltip bottom v-if="userRoles.length > 0">
            <template v-slot:activator="{ on, attrs }">
              <v-chip
                x-small
                outlined
                class="ml-2"
                v-bind="attrs"
                v-on="on"
              >
                {{ userRoles.length }} {{ userRoles.length === 1 ? 'role' : 'roles' }}
              </v-chip>
            </template>
            <span>{{ userRoles.join(', ') }}</span>
          </v-tooltip>
        </div>
      </v-app-bar>

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

  export default {
    name: 'LayoutApp',
    components: {
      Snackbar,
    },
    data: () => ({
      show: true,
    }),
    mounted() {
      if (!this.isInitializing) {
        if (!this.isLoggedIn) {
          console.log("User is not logged in and trying to access logged-in users page")
          this.$router.push("/user/logout")
        }
      }
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
        return this.$store.getters.isInitializing
      },
      isLoggedIn() {
        return this.$store.getters.isLoggedIn || false
      },
      isAdmin() {
        let currentUser = this.$store.getters.user
        if (!currentUser) return false

        if (currentUser.role == "admin") return true
        if (currentUser.roles && currentUser.roles.includes("admin")) return true
        return false
      },
      userEmail() {
        if (!this.$store.getters.user) return ""
        return this.$store.getters.user.email || ""
      },
      userRoles() {
        if (!this.$store.getters.user) return []
        return this.$store.getters.user.roles || []
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
.user-info-container {
  margin-left: auto;
  display: flex;
  align-items: center;
  padding-right: 10px;
}

.user-email-link {
  color: white;
  opacity: 90%;
  cursor: pointer;
  text-decoration: underline;
  text-decoration-style: dotted;
  font-size: 14px;
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
</style>