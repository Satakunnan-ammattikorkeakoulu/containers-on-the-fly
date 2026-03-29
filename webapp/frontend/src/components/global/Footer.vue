<template>
  <footer id="footer" class="background-violet">
    <p>{{appName}}</p>
  </footer>
</template>

<script>
  import { useMainStore } from '@/store/store'
  export default {
    name: 'Footer',
    setup() {
      const store = useMainStore()
      return { store }
    },
    computed: {
      appName() {
        return this.store.appName
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
