import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import { fileURLToPath } from 'url'
import path from 'path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const testsDir = path.resolve(__dirname, '../../tests/frontend')
const nm = (pkg) => path.resolve(__dirname, 'node_modules', pkg)

export default defineConfig({
  plugins: [
    vue(),
    vuetify({ autoImport: true })
  ],
  resolve: {
    extensions: ['.mjs', '.js', '.ts', '.jsx', '.tsx', '.json', '.vue'],
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '/src': fileURLToPath(new URL('./src', import.meta.url)),
    }
  },
  server: {
    host: true,
    port: 8080,
    fs: {
      allow: ['.', testsDir],
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [path.resolve(testsDir, 'setup.js')],
    include: [testsDir + '/**/*.test.js'],
    server: {
      deps: {
        inline: ['vuetify'],
      },
    },
    alias: [
      { find: '@', replacement: fileURLToPath(new URL('./src', import.meta.url)) },
      { find: '/src', replacement: fileURLToPath(new URL('./src', import.meta.url)) },
      { find: 'pinia', replacement: nm('pinia') },
      { find: '@vue/test-utils', replacement: nm('@vue/test-utils') },
      { find: '@pinia/testing', replacement: nm('@pinia/testing') },
      { find: 'vue', replacement: nm('vue') },
      { find: 'dayjs', replacement: nm('dayjs') },
      { find: 'axios', replacement: nm('axios') },
    ],
  }
})
