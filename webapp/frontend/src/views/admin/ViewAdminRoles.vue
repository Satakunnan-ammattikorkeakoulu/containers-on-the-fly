<template>
  <LayoutApp>
    <div id="view-login">
      <v-slide-x-transition mode="out-in">
        <PageAdminRoles />
      </v-slide-x-transition>
    </div>
  </LayoutApp>
</template>

<script>
  import LayoutApp from '/src/layouts/LayoutApp'
  import PageAdminRoles from '/src/pages/admin/PageAdminRoles'

  export default {
    name: 'ViewAdminRoles',

    components: {
      LayoutApp,
      PageAdminRoles,
    },
  }
</script>

<style scoped lang="scss">
</style> 