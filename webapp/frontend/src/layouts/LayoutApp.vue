<template>
  <div v-if="!isInitializing">
    <v-app v-if="isLoggedIn">
      <v-app-bar app elevation="4">
        <a @click="reservations">Reservations</a>
        <a @click="logout">Logout</a>
        <!--<a @click="profile">Profile</a>-->
        <div class="admin-block" v-if="isAdmin">
          <p class="admin-text">Admin</p>
          <a href="/admin/general">General</a>
          <a href="/admin/reservations">Reservations</a>
          <a href="/admin/users">Users</a>
          <a href="/admin/roles">Roles</a>
          <a href="/admin/computers">Computers</a>
          <a href="/admin/containers">Containers</a>
        </div>
        <p class="loggedInText" v-if="isLoggedIn == true">
          Logged in as
          <br />
          <span>{{userEmail}}</span>
        </p>
      </v-app-bar>

      <v-main>
        <v-container>
          <slot></slot>
        </v-container>
      </v-main>
      
      <Footer />
      <Snackbar></Snackbar>
    </v-app>
  </div>
</template>

<script>
  import Snackbar from '/src/components/global/Snackbar.vue';
  import Footer from '/src/components/global/Footer'

  export default {
    name: 'LayoutApp',
    components: {
      Snackbar,
      Footer,
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
        console.log("IMPLEMENT")
        //this.$router.push("/user/reservations")
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
        return false
      },
      userEmail() {
        if (!this.$store.getters.user) return ""
        return this.$store.getters.user.email || ""
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
.loggedInText {
  margin-left: auto;
  margin-top: 15px;
  font-size: 80%;
  color: #717171;
  text-align: right;
  padding-right: 10px;
}
.loggedInText span {
  color: white;
  opacity: 80%;
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