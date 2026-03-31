import { describe, it, expect } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import Loading from '@/components/global/Loading.vue'

describe('Loading', () => {
  it('renders a div wrapper', () => {
    const wrapper = shallowMount(Loading, {
      global: { stubs: { 'v-progress-circular': true } },
    })
    expect(wrapper.find('div').exists()).toBe(true)
  })

  it('accepts a size prop', () => {
    const wrapper = shallowMount(Loading, {
      props: { size: '80px' },
      global: { stubs: { 'v-progress-circular': true } },
    })
    expect(wrapper.props('size')).toBe('80px')
  })

  it('defaults size to 50px', () => {
    const wrapper = shallowMount(Loading, {
      global: { stubs: { 'v-progress-circular': true } },
    })
    expect(wrapper.props('size')).toBe('50px')
  })
})
