<template>
  <div>
  </div>
</template>

<script>
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