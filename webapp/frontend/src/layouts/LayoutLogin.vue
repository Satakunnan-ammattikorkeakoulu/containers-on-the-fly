<template>
  <div>
    <slot></slot>
    <Snackbar></Snackbar>
  </div>
</template>

<script>
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