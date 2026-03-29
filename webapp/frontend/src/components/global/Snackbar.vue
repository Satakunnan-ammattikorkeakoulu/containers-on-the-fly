<!--
  Global snackbar component. Hooked to Pinia store.
  Use with: store.showMessage({ text: "", color: "" });
-->
<template>
  <v-snackbar
    v-model="snackbar.visible"
    :timeout="snackbar.timeout"
    :color="snackbar.color"
    location="bottom end"
    :multi-line="snackbar.multiline === true">
      {{ snackbar.text }}  
      <v-btn v-if="snackbar.close" dark @click="closeMessage">Close</v-btn>
  </v-snackbar>
</template>

<script>
  import { useMainStore } from '@/store/store'
  export default {
    setup() {
      const store = useMainStore()
      return { store }
    },
    computed: {
      snackbar() {
        return this.store.snackbar
      }
    },
    methods: {
      closeMessage() {
        this.store.closeMessage()
      }
    }
  }
</script>