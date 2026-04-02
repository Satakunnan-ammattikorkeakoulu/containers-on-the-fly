<template>
  <LayoutApp>
    <div id="view-login">
      <v-slide-x-transition mode="out-in">
        <PageAdminAuditLog />
      </v-slide-x-transition>
    </div>
  </LayoutApp>
</template>

<script>
  /**
   * View wrapper for the admin audit log page. Renders PageAdminAuditLog inside LayoutApp.
   */
  import LayoutApp from '/src/layouts/LayoutApp'
  import PageAdminAuditLog from '/src/pages/admin/PageAdminAuditLog'

  export default {
    name: 'ViewAdminAuditLog',

    components: {
      LayoutApp,
      PageAdminAuditLog,
    },
  }
</script>

<style scoped lang="scss">
</style>
