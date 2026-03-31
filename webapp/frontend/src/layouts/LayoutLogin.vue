<template>
  <div>
    <slot></slot>
    <Snackbar></Snackbar>
  </div>
</template>

<script>
  /**
   * Minimal layout for unauthenticated pages (login). Renders slotted content
   * with only a global Snackbar -- no navigation bar or sidebar.
   */
  import Snackbar from '/src/components/global/Snackbar.vue';

  export default {
    name: 'LayoutLogin',
    components: {
      Snackbar,
    },
  }
</script>

<style scoped lang="scss">
</style>