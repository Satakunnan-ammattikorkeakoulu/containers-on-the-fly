<template>
  <LayoutApp>
    <div id="view-admin-general">
      <v-slide-x-transition mode="out-in">
        <PageAdminGeneral />
      </v-slide-x-transition>
    </div>
  </LayoutApp>
</template>

<script>
  import LayoutApp from '/src/layouts/LayoutApp'
  import PageAdminGeneral from '/src/pages/admin/PageAdminGeneral'

  export default {
    name: 'ViewAdminGeneral',

    components: {
      LayoutApp,
      PageAdminGeneral,
    },
  }
</script>

<style scoped lang="scss">
</style> 