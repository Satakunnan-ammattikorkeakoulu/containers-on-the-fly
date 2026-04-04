<template>
  <div>
    <slot></slot>
    <Snackbar></Snackbar>
    <ConfirmDialog></ConfirmDialog>
    <PromptDialog></PromptDialog>
  </div>
</template>

<script>
  /**
   * Minimal layout for unauthenticated pages (login). Renders slotted content
   * with only a global Snackbar -- no navigation bar or sidebar.
   */
  import Snackbar from '/src/components/global/Snackbar.vue';
  import ConfirmDialog from '/src/components/global/ConfirmDialog.vue';
  import PromptDialog from '/src/components/global/PromptDialog.vue';

  export default {
    name: 'LayoutLogin',
    components: {
      Snackbar,
      ConfirmDialog,
      PromptDialog,
    },
  }
</script>

<style scoped lang="scss">
</style>