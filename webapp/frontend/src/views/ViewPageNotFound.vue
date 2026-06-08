<template>
  <div id="section-notfound">
    <h1 style="margin-bottom: 10px;">Page not found</h1>
    <p>This page could not be found.</p>
    <p><a @click="navigateHome">Back to home page</a></p>
  </div>
</template>

<script>
  /**
   * 404 page displayed for unmatched routes.
   */
  export default {
    name: 'ViewPageNotFound',

    components: {

    },
    methods: {
      navigateHome() {
        this.$router.push("/")
      },
    },
  }
</script>

<style scoped lang="scss">
  #section-notfound {
    margin: 100px auto;
    text-align: center;
  }
</style>