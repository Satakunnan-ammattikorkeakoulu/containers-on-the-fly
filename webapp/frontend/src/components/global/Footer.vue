<template>
  <footer id="footer" class="background-violet">
    <p>{{appName}}</p>
  </footer>
</template>

<script>
  export default {
    name: 'Footer',
    computed: {
      appName() {
        return this.$store.getters.appName
      }
    },
  }
</script>

<style scoped lang="scss">
  #footer {
    width: 100%;
    height: auto;
    text-align: center;
    background: var(--v-primary-base);
    color: var(--v-primary-text);
    margin: 0px;
    padding: 30px;
  }

  #footer p {
    margin: 0px;
  }
</style>
