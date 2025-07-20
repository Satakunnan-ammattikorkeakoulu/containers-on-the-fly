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
import ErrorTemplate from '@/components/global/ErrorTemplate.vue'

export default {
  name: 'App',
  components: {
    ErrorTemplate
  },
  computed: {
    hasConfigError() {
      return this.$store.getters.hasConfigError;
    },
    configErrorMessage() {
      return this.$store.getters.configErrorMessage;
    },
    appName() {
      return this.$store.getters.appName;
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
  .fade-enter, .fade-leave-to {
    opacity: 0;
  }
</style>