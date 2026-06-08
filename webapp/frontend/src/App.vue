<template>
  <v-app>
    <v-main>
      <!-- Show error template if config loading failed -->
      <ErrorTemplate 
        v-if="hasConfigError" 
        :error-message="configErrorMessage"
      />
      <!-- Normal app content -->
      <transition name="fade" v-else>
        <router-view/>
      </transition>
    </v-main>
  </v-app>
</template>

<script>
/**
 * Root application component. Renders the router view or a full-page error screen
 * when the application configuration fails to load. Keeps the document title in
 * sync with the app name from the store.
 */
import ErrorTemplate from '@/components/global/ErrorTemplate.vue'
import { useMainStore } from '@/store/store'

export default {
  name: 'App',
  setup() {
    const store = useMainStore()
    return { store }
  },
  components: {
    ErrorTemplate
  },
  computed: {
    hasConfigError() {
      return this.store.hasConfigError;
    },
    configErrorMessage() {
      return this.store.configErrorMessage;
    },
    appName() {
      return this.store.appName;
    }
  },
  data: () => ({
  }),
  watch: {
    appName: {
      handler(newAppName) {
        if (newAppName) {
          document.title = newAppName;
        }
      },
      immediate: true
    }
  },
};
</script>

<style scoped>
  .fade-enter-active, .fade-leave-active {
    transition: opacity .2s;
  }
  .fade-enter-from, .fade-leave-to {
    opacity: 0;
  }
</style>