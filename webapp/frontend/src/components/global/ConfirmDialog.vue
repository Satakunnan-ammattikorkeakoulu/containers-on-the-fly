<!--
  Global confirmation dialog component. Hooked to Pinia store.
  Use with: const confirmed = await store.showConfirmDialog({ title, message, ... });
-->
<template>
  <v-dialog v-model="dialog.visible" persistent max-width="500">
    <v-card>
      <v-card-title class="px-8 pt-6">{{ dialog.title }}</v-card-title>
      <v-card-text class="px-8">{{ dialog.message }}</v-card-text>
      <v-card-actions class="px-8 pb-5">
        <v-spacer />
        <v-btn variant="text" @click="cancel">{{ dialog.cancelText }}</v-btn>
        <v-btn :color="dialog.confirmColor" variant="flat" @click="confirm">
          {{ dialog.confirmText }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
  /**
   * Global confirmation dialog driven by the Pinia store's confirmDialog state.
   * Replaces native window.confirm() calls throughout the application.
   */
  import { useMainStore } from '@/store/store'
  export default {
    setup() {
      const store = useMainStore()
      return { store }
    },
    computed: {
      dialog() {
        return this.store.confirmDialog
      }
    },
    methods: {
      confirm() {
        this.store.resolveConfirmDialog(true)
      },
      cancel() {
        this.store.resolveConfirmDialog(false)
      }
    }
  }
</script>
