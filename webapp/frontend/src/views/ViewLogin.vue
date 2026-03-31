<template>
  <LayoutLogin>
    <div id="view-login">
      <v-slide-x-transition mode="out-in">
        <PageLogin />
      </v-slide-x-transition>
    </div>
  </LayoutLogin>
</template>

<script>
  /**
   * View wrapper for the login page. Renders PageLogin inside LayoutLogin.
   */
  import LayoutLogin from '/src/layouts/LayoutLogin'
  import PageLogin from '/src/pages/common/PageLogin'

  export default {
    name: 'ViewLogin',

    components: {
      PageLogin,
      LayoutLogin,
    },
  }
</script>

<style scoped lang="scss">
  #view-login {
    margin: 50px auto;
    text-align: center;
  }
</style>