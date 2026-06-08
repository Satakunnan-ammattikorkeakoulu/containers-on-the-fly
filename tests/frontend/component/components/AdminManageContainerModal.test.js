import { describe, it, expect, vi, beforeEach } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'

// Local axios mock — the shared setup.js mock only exposes `.get/.post` and
// this modal calls axios as a function (`axios({ method, url, ... })`), so we
// need a callable mock here.
vi.mock('axios', () => {
  const mockFn = vi.fn(() => Promise.resolve({ data: { status: true, data: {} } }))
  return { default: mockFn }
})

import axios from 'axios'
import AdminManageContainerModal from '@/components/admin/AdminManageContainerModal.vue'

function mountModal(propData = 'new') {
  return shallowMount(AdminManageContainerModal, {
    props: { propData },
    global: {
      plugins: [createTestingPinia({ initialState: { main: { user: { loginToken: 'fake' } } } })],
      mocks: {
        $appSettings: {
          APIServer: {
            admin: {
              save_container: '/api/admin/save_container',
              container_defaults: '/api/admin/container_defaults',
              container_templates: '/api/admin/container_templates',
              get_container: '/api/admin/container',
            },
          },
        },
      },
      stubs: {
        AdminBuildLogDialog: true,
        'v-form': {
          template: '<form><slot /></form>',
          methods: { validate() { return true } },
        },
        'v-dialog': { template: '<div class="v-dialog"><slot /></div>', props: ['modelValue'] },
        'v-card': { template: '<div><slot /></div>' },
        'v-card-text': { template: '<div><slot /></div>' },
        'v-card-actions': { template: '<div><slot /></div>' },
        'v-container': { template: '<div><slot /></div>' },
        'v-row': { template: '<div><slot /></div>' },
        'v-col': { template: '<div><slot /></div>' },
        'v-tooltip': { template: '<div><slot name="activator" :props="{}" /><slot /></div>' },
        'v-text-field': true,
        'v-textarea': true,
        'v-btn': true,
        'v-switch': true,
        'v-radio-group': true,
        'v-radio': true,
        'v-alert': true,
        'v-chip': true,
        'v-progress-circular': true,
        'v-select': true,
        'v-icon': true,
        'v-expansion-panels': true,
        'v-expansion-panel': true,
        'v-expansion-panel-title': true,
        'v-expansion-panel-text': true,
        'v-card-title': true,
        'v-spacer': true,
      },
    },
  })
}

describe('AdminManageContainerModal', () => {
  beforeEach(() => {
    axios.mockClear()
    axios.mockResolvedValue({ data: { status: true, data: {} } })
  })

  describe('imageNameLocked', () => {
    it('is false when creating a new container', () => {
      const wrapper = mountModal('new')
      expect(wrapper.vm.imageNameLocked).toBe(false)
    })

    it('is true when editing a built container (lastBuiltAt set)', () => {
      const wrapper = mountModal('new')
      wrapper.vm.isCreatingNew = false
      wrapper.vm.data.lastBuiltAt = '2026-01-01T00:00:00Z'
      wrapper.vm.data.buildStatus = 'success'
      expect(wrapper.vm.imageNameLocked).toBe(true)
    })

    it('is true when editing a container that is currently building', () => {
      const wrapper = mountModal('new')
      wrapper.vm.isCreatingNew = false
      wrapper.vm.data.lastBuiltAt = null
      wrapper.vm.data.buildStatus = 'building'
      expect(wrapper.vm.imageNameLocked).toBe(true)
    })

    it('is false when editing a never-built container', () => {
      const wrapper = mountModal('new')
      wrapper.vm.isCreatingNew = false
      wrapper.vm.data.lastBuiltAt = null
      wrapper.vm.data.buildStatus = null
      expect(wrapper.vm.imageNameLocked).toBe(false)
    })

    it('is false when editing a container whose build failed and was never built before', () => {
      const wrapper = mountModal('new')
      wrapper.vm.isCreatingNew = false
      wrapper.vm.data.lastBuiltAt = null
      wrapper.vm.data.buildStatus = 'failed'
      expect(wrapper.vm.imageNameLocked).toBe(false)
    })

    it('is false when switching a built container to externally-managed', async () => {
      const wrapper = mountModal('new')
      await wrapper.setData({
        isCreatingNew: false,
        data: {
          ...wrapper.vm.data,
          lastBuiltAt: '2026-01-01T00:00:00Z',
          buildStatus: 'success',
          managedExternally: true,
        },
      })
      expect(wrapper.vm.isExternallyManaged).toBe(true)
      expect(wrapper.vm.imageNameLocked).toBe(false)
    })
  })

  describe('willRebuild', () => {
    it('returns true when imageName changes on an Image Builder container', () => {
      const wrapper = mountModal('new')
      wrapper.vm.isCreatingNew = false
      wrapper.vm.data.managedExternally = false
      wrapper.vm.data.dockerfileCommands = 'RUN echo hi'
      wrapper.vm.data.imageName = 'new-name'
      wrapper.vm.originalImageFields = {
        imageName: 'old-name',
        dockerfileCommands: 'RUN echo hi',
        baseImage: 'ubuntu:24.04',
        containerUsername: 'user',
        containerCmd: '["/bin/bash"]',
      }
      wrapper.vm.data.baseImage = 'ubuntu:24.04'
      wrapper.vm.data.containerUsername = 'user'
      wrapper.vm.data.containerCmd = '["/bin/bash"]'
      expect(wrapper.vm.willRebuild).toBe(true)
    })
  })

  describe('overwrite confirmation dialog', () => {
    it('opens when the backend returns needsOverwriteConfirmation', async () => {
      const wrapper = mountModal('new')
      // Drain the axios calls from created() (fetchDefaults/fetchTemplates)
      await new Promise(r => setTimeout(r, 0))
      axios.mockClear()
      axios.mockResolvedValueOnce({
        data: {
          status: false,
          message: 'Image already exists',
          data: { needsOverwriteConfirmation: true, imageName: 'collision-image' },
        },
      })

      wrapper.vm.data.name = 'Foo'
      wrapper.vm.data.imageName = 'collision-image'
      wrapper.vm.data.ports = [{ serviceName: 'SSH', port: 22 }]

      await wrapper.vm.submit()
      await new Promise(r => setTimeout(r, 0))

      expect(wrapper.vm.showOverwriteDialog).toBe(true)
      expect(wrapper.vm.overwriteDialogImageName).toBe('collision-image')
    })

    it('confirmOverwriteAndSave sets the flag and retriggers save', async () => {
      const wrapper = mountModal('new')
      await new Promise(r => setTimeout(r, 0))
      axios.mockClear()

      wrapper.vm.data.name = 'Foo'
      wrapper.vm.data.imageName = 'collision-image'
      wrapper.vm.data.ports = [{ serviceName: 'SSH', port: 22 }]
      wrapper.vm.showOverwriteDialog = true

      axios.mockResolvedValueOnce({
        data: { status: true, data: { containerId: 42 } },
      })

      wrapper.vm.confirmOverwriteAndSave()
      await new Promise(r => setTimeout(r, 0))

      expect(wrapper.vm.showOverwriteDialog).toBe(false)
      expect(wrapper.vm.data.confirmOverwrite).toBe(true)
      // The save axios call must include confirmOverwrite: true.
      const saveCall = axios.mock.calls.find(
        c => c[0] && c[0].url && c[0].url.includes('save_container')
      )
      expect(saveCall).toBeDefined()
      expect(saveCall[0].data.data.confirmOverwrite).toBe(true)
    })

    it('cancelOverwrite closes the dialog and clears the flag', () => {
      const wrapper = mountModal('new')
      wrapper.vm.showOverwriteDialog = true
      wrapper.vm.data.confirmOverwrite = true

      wrapper.vm.cancelOverwrite()

      expect(wrapper.vm.showOverwriteDialog).toBe(false)
      expect(wrapper.vm.data.confirmOverwrite).toBe(false)
    })
  })
})
