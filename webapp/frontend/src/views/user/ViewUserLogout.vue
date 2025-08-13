<template>
  <div>
  </div>
</template>

<script>
  export default {
    name: 'ViewUserLogout',

    components: {
    },
    mounted() {
      // Logout user and redirect immediately
      this.$store.commit("logoutUser")
      console.log("logged out...")
      this.$router.push("/")
    },
  }
</script>

<style scoped lang="scss">
</style>