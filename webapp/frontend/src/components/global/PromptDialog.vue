<!--
  Global prompt dialog component. Hooked to Pinia store.
  Use with: const value = await store.showPromptDialog({ title, message, inputLabel, ... });
-->
<template>
  <v-dialog v-model="dialog.visible" persistent max-width="500">
    <v-card>
      <v-card-title class="px-8 pt-6">{{ dialog.title }}</v-card-title>
      <v-card-text class="px-8 pb-2">
        <p v-if="dialog.message" class="mb-10">{{ dialog.message }}</p>
        <v-text-field
          v-model="inputValue"
          :label="dialog.inputLabel"
          :rules="dialog.rules"
          :type="dialog.inputType || 'text'"
          :min="dialog.min"
          :max="dialog.max"
          :maxlength="dialog.maxlength"
          :counter="dialog.counter"
          variant="outlined"
          autofocus
          @keyup.enter="confirm"
        />
      </v-card-text>
      <v-card-actions class="px-8 pb-5">
        <v-spacer />
        <v-btn variant="text" @click="cancel">Cancel</v-btn>
        <v-btn color="primary" variant="flat" @click="confirm">OK</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
  /**
   * Global prompt dialog driven by the Pinia store's promptDialog state.
   * Replaces native prompt() calls throughout the application.
   */
  import { useMainStore } from '@/store/store'
  export default {
    setup() {
      const store = useMainStore()
      return { store }
    },
    data() {
      return {
        inputValue: ''
      }
    },
    computed: {
      dialog() {
        return this.store.promptDialog
      }
    },
    watch: {
      'dialog.visible'(isVisible) {
        if (isVisible) {
          this.inputValue = this.dialog.defaultValue || ''
        }
      }
    },
    methods: {
      confirm() {
        this.store.resolvePromptDialog(this.inputValue)
      },
      cancel() {
        this.store.resolvePromptDialog(null)
      }
    }
  }
</script>
