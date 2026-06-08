import { describe, it, expect } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import ErrorTemplate from '@/components/global/ErrorTemplate.vue'

// Use slot-rendering stubs so text content is accessible
const slotStub = { template: '<div><slot /></div>' }
const vuetifyStubs = {
  'v-container': slotStub,
  'v-row': slotStub,
  'v-col': slotStub,
  'v-card': slotStub,
  'v-icon': slotStub,
  'v-btn': slotStub,
}

describe('ErrorTemplate', () => {
  it('renders without error', () => {
    const wrapper = shallowMount(ErrorTemplate, {
      global: { stubs: vuetifyStubs },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('displays default message when no prop', () => {
    const wrapper = shallowMount(ErrorTemplate, {
      global: { stubs: vuetifyStubs },
    })
    expect(wrapper.text()).toContain('could not connect')
  })

  it('displays custom error message', () => {
    const wrapper = shallowMount(ErrorTemplate, {
      props: { errorMessage: 'Custom error occurred' },
      global: { stubs: vuetifyStubs },
    })
    expect(wrapper.text()).toContain('Custom error occurred')
  })

  it('displays configuration error title', () => {
    const wrapper = shallowMount(ErrorTemplate, {
      global: { stubs: vuetifyStubs },
    })
    expect(wrapper.text()).toContain('Configuration Error')
  })
})
