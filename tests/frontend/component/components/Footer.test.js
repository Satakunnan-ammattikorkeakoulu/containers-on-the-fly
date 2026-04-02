import { describe, it, expect } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Footer from '@/components/global/Footer.vue'

describe('Footer', () => {
  it('renders footer element', () => {
    setActivePinia(createPinia())
    const wrapper = shallowMount(Footer)
    expect(wrapper.find('#footer').exists()).toBe(true)
  })

  it('displays app name', () => {
    setActivePinia(createPinia())
    const wrapper = shallowMount(Footer)
    // Default app name
    expect(wrapper.text()).toContain('Containers on the Fly')
  })
})
