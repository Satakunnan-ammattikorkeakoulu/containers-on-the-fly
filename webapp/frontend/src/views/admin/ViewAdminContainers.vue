<template>
  <LayoutApp>
    <div id="view-login">
      <v-slide-x-transition mode="out-in">
        <PageAdminContainers />
      </v-slide-x-transition>
    </div>
  </LayoutApp>
</template>

<script>
  import LayoutApp from '/src/layouts/LayoutApp'
  import PageAdminContainers from '/src/pages/admin/PageAdminContainers'

  export default {
    name: 'ViewAdminContainers',

    components: {
      LayoutApp,
      PageAdminContainers,
    },
  }
</script>

<style scoped lang="scss">
</style>