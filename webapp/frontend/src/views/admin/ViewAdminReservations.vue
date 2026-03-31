<template>
  <LayoutApp>
    <div id="view-login">
      <v-slide-x-transition mode="out-in">
        <PageAdminReservations />
      </v-slide-x-transition>
    </div>
  </LayoutApp>
</template>

<script>
  /**
   * View wrapper for the admin reservations management page. Renders PageAdminReservations inside LayoutApp.
   */
  import LayoutApp from '/src/layouts/LayoutApp'
  import PageAdminReservations from '/src/pages/admin/PageAdminReservations'

  export default {
    name: 'ViewAdminReservations',

    components: {
      LayoutApp,
      PageAdminReservations,
    },
  }
</script>

<style scoped lang="scss">
</style>