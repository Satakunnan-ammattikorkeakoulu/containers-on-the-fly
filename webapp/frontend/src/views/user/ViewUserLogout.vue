<template>
  <div>
  </div>
</template>

<script>
  /**
   * Logout view. Clears the user session on mount and redirects to the login page.
   */
  import { useMainStore } from '@/store/store'

  export default {
    name: 'ViewUserLogout',

    setup() {
      const store = useMainStore()
      return { store }
    },

    components: {
    },
    mounted() {
      // Logout user and redirect immediately
      this.store.logoutUser()
      console.log("logged out...")
      this.$router.push("/")
    },
  }
</script>

<style scoped lang="scss">
</style>