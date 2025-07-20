import Vue from 'vue'
import Vuex from 'vuex'
const axios = require('axios').default;
import AppSettings from '/src/AppSettings.js';

Vue.use(Vuex);

// Helper function for responses
function Response(success, message) {
  return { success, message };
}

// Global VUEX store
export const store = new Vuex.Store({
  // ##########
  // # STATES #
  // ##########
  state: {
    // For global snackbar (message) component
    snackbar: {
      text: null, // Text for snackbar
      color: "primary", // Color for snackbar
      visible: false, // Is the snackbar visible
      close: false, // Does user see close button
      timeout: 7000, // Default timeout for snackbars
      multiline: false, // Is this multiline, automatically set below
    },
    initializing: true, // Set to false after we have initialized the app / store
    // Information about the currently logged-in user
    user: {
      loginToken: "",
      email: "",
      role: "",
      loggedinAt: null
    },
    // App configuration from backend
    appConfig: {
      app: {
        name: "",
        timezone: "",
        contactEmail: ""
      },
      reservation: {
        minimumDuration: 5,
        maximumDuration: 72
      },
      instructions: {
        login: "",
        reservation: "",
        email: "",
        usernameFieldLabel: "",
        passwordFieldLabel: ""
      },
      login: {
        loginText: "Login with your credentials.",
        usernameField: "Username",
        passwordField: "Password"
      }
    },
    configLoaded: false,
    configError: false,
    configErrorMessage: ""
  },
  // ###########
  // # GETTERS #
  // ###########
  getters: {
    // Gets current user data or null
    user: state => {
      return state.user || null
    },
    // Check if user is logged in or not, only in clientside
    isLoggedIn: state => {
      if (state.user && state.user.loginToken) return true
      else return false
    },
    // true if we are loading the app, false otherwise
    isInitializing: state => {
      return state.initializing
    },
    // App configuration getters
    appConfig: state => state.appConfig,
    isConfigLoaded: state => state.configLoaded,
    hasConfigError: state => state.configError,
    configErrorMessage: state => state.configErrorMessage,
    appName: state => state.appConfig.app.name || AppSettings.General.appName,
    appTimezone: state => state.appConfig.app.timezone || AppSettings.General.timezone,
    contactEmail: state => state.appConfig.app.contactEmail || AppSettings.General.contactEmail,
    reservationMinDuration: state => state.appConfig.reservation.minimumDuration,
    reservationMaxDuration: state => state.appConfig.reservation.maximumDuration,
    loginPageInfo: state => state.appConfig.instructions.login,
    reservationPageInstructions: state => state.appConfig.instructions.reservation,
    emailInstructions: state => state.appConfig.instructions.email,
    loginText: state => state.appConfig.login.loginText,
    usernameField: state => state.appConfig.instructions.usernameFieldLabel || state.appConfig.login.usernameField || AppSettings.Login.usernameField,
    passwordField: state => state.appConfig.instructions.passwordFieldLabel || state.appConfig.login.passwordField || AppSettings.Login.passwordField
  },
  // #############
  // # MUTATIONS #
  // #############
  mutations: {
    // eslint-disable-next-line
    initialiseStore(state, payload) {
      // Load app configuration first, then check for user login
      this.dispatch('loadAppConfig').then(() => {
        // Only continue if config loaded successfully (no error state)
        if (!state.configError) {
          // Apply all permanent localStorage items to store here
          try {
            let user = localStorage.getItem("user")
            if (user) {
              user = JSON.parse(user)
              this.commit("setUser", {
                "loginToken": user.loginToken,
                "email": user.email,
                "role": user.role,
                "loggedinAt": user.loggedinAt
              });
            }
            else {
              state.initializing = false
            }
          }
          catch (e) {
            console.log("Error parsing initializeStore items:", e)
            state.initializing = false
          }
        }
        // If config error exists, initialization stops and error page shows
      }).catch(() => {
        // This catch should not be reached now since we handle errors in loadAppConfig
        state.initializing = false
      });
    },
    
    setAppConfig(state, config) {
      state.appConfig = { ...state.appConfig, ...config };
      state.configLoaded = true;
      state.configError = false;
      state.configErrorMessage = "";
    },
    
    setConfigError(state, errorMessage) {
      state.configError = true;
      state.configErrorMessage = errorMessage;
      state.configLoaded = false;
    },
    
    clearConfigError(state) {
      state.configError = false;
      state.configErrorMessage = "";
    },
    
    // Sets currently logged-in user data
    setUser(state, payload) {
      if (!payload.callback) payload.callback = () => { };

      if (!payload.loginToken) return payload.callback(Response(false, "loginToken was missing"));
      let _this = this;
      
      axios({
        method: "get",
        url: AppSettings.APIServer.user.check_token,
        headers: {"Authorization" : `Bearer ${payload.loginToken}`}
      })
      .then(function (response) {
          // Success
          if (response.data.status == true) {
            state.user.loginToken = payload.loginToken
            state.user.email = response.data.data.email
            state.user.role = response.data.data.role
            state.user.loggedinAt = new Date()
            localStorage.setItem("user", JSON.stringify(state.user))
            if (state.initializing) state.initializing = false
            return payload.callback(Response(true, "Login token OK!"));
          }
          // Fail
          else {
            console.log("Invalid token – logging user out.")
            _this.commit("logoutUser")
            if (state.initializing) state.initializing = false
            return payload.callback(Response(false, "Invalid login token."));
          }
      })
      .catch(function (error) {
          // Error
          if (error.response && error.response.status == 400) {
            return payload.callback(Response(false, error.response.data.detail));
          }
          // Unauthorized
          else if (error.response && error.response.status == 401) {
            console.log("Unauthorized – Logging user out.")
            _this.commit("logoutUser")
            if (state.initializing) state.initializing = false
            return payload.callback(Response(false, "Invalid login token."));
          }
          else {
            console.log(error)
            return payload.callback(Response(false, "Unknown error."));
          }
      });
    },
    
    // Logs out currently logged in user
    logoutUser(state) {
      localStorage.removeItem("user")
      state.user.loginToken = ""
      state.user.email = ""
      state.user.role = ""
      state.user.loggedinAt = null
    },
    
    // Shows global snackbar message
    showMessage(state, payload) {
      state.snackbar.text = payload.text;
      state.snackbar.color = payload.color || "primary";
      state.snackbar.close = payload.close || false;
      state.snackbar.multiline = (payload.text.length > 50) ? true : false;

      if (payload.multiline) {
        state.snackbar.multiline = payload.multiline;
      }

      if (payload.timeout) {
        state.snackbar.timeout = payload.timeout;
      }

      state.snackbar.visible = true;
    },
    
    // Closes the global snackbar
    closeMessage(state) {
      state.snackbar.visible = false;
    }
  },
  
  // ###########
  // # ACTIONS #
  // ###########
  actions: {
    async loadAppConfig({ commit }) {
      try {
        const response = await axios.get(AppSettings.APIServer.app.get_config);
        if (response.data.status) {
          commit('setAppConfig', response.data.data);
        } else {
          console.error('Failed to load app config:', response.data.message);
          commit('setConfigError', response.data.message || 'Failed to load application configuration');
          return; // Don't continue with user initialization
        }
      } catch (error) {
        console.error('Error loading app config:', error);
        const errorMessage = error.response?.data?.message || error.message || 'Unable to connect to server';
        commit('setConfigError', `Error loading app configuration: ${errorMessage}`);
        return; // Don't continue with user initialization
      }
    }
  }
})