<template>
  <LayoutApp>
    <div id="view-login">
      <v-slide-x-transition mode="out-in">
        <PageUserReserve />
      </v-slide-x-transition>
    </div>
  </LayoutApp>
</template>

<script>
  /**
   * View wrapper for the new reservation page. Renders PageUserReserve inside LayoutApp.
   */
  import LayoutApp from '/src/layouts/LayoutApp'
  import PageUserReserve from '/src/pages/user/PageUserReserve'

  export default {
    name: 'ViewUserReserve',

    components: {
      LayoutApp,
      PageUserReserve,
    },
  }
</script>

<style scoped lang="scss">
</style>