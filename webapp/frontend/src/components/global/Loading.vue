<!--
  Global loading indicator.
-->
<template>
  <div>
    <v-progress-circular :style="styles" indeterminate color="primary"></v-progress-circular>
  </div>
</template>

<script>
  /**
   * Centered circular progress indicator with configurable size.
   */
  export default {
    name: "Loading",
    props: {
      size: {
        type: String,
        default: "50px",
      },
    },
    methods: {
      styles () {
        return `width: ${this.size} !important; height: ${this.size} !important;`;
      }
    }
  }
</script>

<style scoped>
  div {
    text-align: center;
  }
</style>