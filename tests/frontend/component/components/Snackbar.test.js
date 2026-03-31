import { describe, it, expect, beforeEach } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { useMainStore } from '@/store/store.js'
import Snackbar from '@/components/global/Snackbar.vue'

function mountSnackbar(snackbarState = {}) {
  return shallowMount(Snackbar, {
    global: {
      plugins: [
        createTestingPinia({
          initialState: {
            main: {
              snackbar: {
                text: 'Test message',
                color: 'green',
                visible: true,
                close: false,
                timeout: 7000,
                multiline: false,
                ...snackbarState,
              },
            },
          },
        }),
      ],
      stubs: {
        'v-snackbar': { template: '<div class="v-snackbar"><slot /></div>', props: ['modelValue'] },
        'v-btn': true,
      },
    },
  })
}

describe('Snackbar', () => {
  it('renders snackbar text from store', () => {
    const wrapper = mountSnackbar({ visible: true, text: 'Hello world' })
    expect(wrapper.text()).toContain('Hello world')
  })

  it('has access to store snackbar state', () => {
    mountSnackbar({ visible: true })
    const store = useMainStore()
    expect(store.snackbar.visible).toBe(true)
  })
})
