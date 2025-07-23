import Vue from 'vue'
import App from './App.vue'
import router from './router/router'
import vuetify from './plugins/vuetify'
import AppSettings from '/src/AppSettings.js';
import '/src/main.css';

import { store } from './store/store';
const axios = require('axios').default;

// HTTP interceptors for authentication
axios.interceptors.response.use(
  // Return successful responses as-is
  response => response,
  // Handle errors
  error => {
    // Check for authentication errors
    if (error.response && (error.response.status === 401 || error.response.status === 403)) {
      // Clear user data and redirect to login
      store.commit('logoutUser')
      
      // Only redirect if not already on login/logout pages
      if (router.currentRoute.path !== '/' && router.currentRoute.path !== '/user/logout') {
        router.push('/')
        store.commit('showMessage', { 
          text: 'Your session has expired. Please log in again.', 
          color: 'red' 
        })
      }
    }
    
    // Return the error for component-level handling
    return Promise.reject(error)
  }
)

Vue.config.productionTip = false

new Vue({
  router,
  store,
  vuetify,
  beforeCreate() { this.$store.commit('initialiseStore'); },
  render: h => h(App)
}).$mount('#app')

// Mixins
Vue.mixin({
  computed: {
    AppSettings() {
      return AppSettings;
    }
  }
})