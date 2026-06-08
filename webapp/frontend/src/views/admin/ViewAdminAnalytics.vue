<template>
  <LayoutApp>
    <div id="view-login">
      <v-slide-x-transition mode="out-in">
        <PageAdminAnalytics />
      </v-slide-x-transition>
    </div>
  </LayoutApp>
</template>

<script>
  /**
   * View wrapper for the admin analytics page. Renders PageAdminAnalytics inside LayoutApp.
   */
  import LayoutApp from '/src/layouts/LayoutApp'
  import PageAdminAnalytics from '/src/pages/admin/PageAdminAnalytics'

  export default {
    name: 'ViewAdminAnalytics',

    components: {
      LayoutApp,
      PageAdminAnalytics,
    },
  }
</script>

<style scoped lang="scss">
</style>
