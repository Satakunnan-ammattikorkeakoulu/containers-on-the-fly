import { createApp } from 'vue'
import App from './App.vue'
import router from './router/router'
import vuetify from './plugins/vuetify'
import { createPinia } from 'pinia'
import { useMainStore } from './store/store'
import AppSettings from '/src/AppSettings.js'
import '/src/main.css'
import axios from 'axios'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(vuetify)

// Make AppSettings available globally (replaces Vue.mixin)
app.config.globalProperties.$appSettings = AppSettings

// Initialize the store
const store = useMainStore()

// HTTP interceptors for authentication
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response && (error.response.status === 401 || error.response.status === 403)) {
      store.logoutUser()

      if (router.currentRoute.value.path !== '/' && router.currentRoute.value.path !== '/user/logout') {
        router.push('/')
        store.showMessage({
          text: 'Your session has expired. Please log in again.',
          color: 'red'
        })
      }
    }
    return Promise.reject(error)
  }
)

// Initialize store on app creation
store.initialiseStore()

app.mount('#app')
