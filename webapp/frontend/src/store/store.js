import { defineStore } from 'pinia'
import axios from 'axios'
import AppSettings from '/src/AppSettings.js'

export const useMainStore = defineStore('main', {
  state: () => ({
    // For global snackbar (message) component
    snackbar: {
      text: null,
      color: "primary",
      visible: false,
      close: false,
      timeout: 7000,
      multiline: false,
    },
    initializing: true,
    // Information about the currently logged-in user
    user: {
      loginToken: "",
      email: "",
      role: "",
      roles: [],
      loggedinAt: null,
      reservationLimits: {
        minDuration: 1,
        maxDuration: 48,
        maxActiveReservations: 1
      }
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
      }
    },
    configLoaded: false,
    configError: false,
    configErrorMessage: ""
  }),

  getters: {
    isLoggedIn: (state) => {
      if (state.user && state.user.loginToken) return true
      else return false
    },
    isInitializing: (state) => state.initializing,
    isConfigLoaded: (state) => state.configLoaded,
    hasConfigError: (state) => state.configError,
    appName: (state) => state.appConfig.app.name || 'Containers on the Fly',
    appTimezone: (state) => state.appConfig.app.timezone,
    contactEmail: (state) => state.appConfig.app.contactEmail,
    loginPageInfo: (state) => state.appConfig.instructions.login,
    reservationPageInstructions: (state) => state.appConfig.instructions.reservation,
    emailInstructions: (state) => state.appConfig.instructions.email,
    loginText: (state) => state.appConfig.instructions.login,
    usernameField: (state) => state.appConfig.instructions.usernameFieldLabel,
    passwordField: (state) => state.appConfig.instructions.passwordFieldLabel,
    userReservationLimits: (state) => state.user.reservationLimits,
    userMinDuration: (state) => state.user.reservationLimits.minDuration,
    userMaxDuration: (state) => state.user.reservationLimits.maxDuration,
    userMaxActiveReservations: (state) => state.user.reservationLimits.maxActiveReservations,
  },

  actions: {
    initialiseStore() {
      this.loadAppConfig().then(() => {
        if (!this.configError) {
          try {
            let user = localStorage.getItem("user")
            if (user) {
              user = JSON.parse(user)
              this.setUser({
                "loginToken": user.loginToken,
                "email": user.email,
                "role": user.role,
                "roles": user.roles || [],
                "loggedinAt": user.loggedinAt,
                "reservationLimits": user.reservationLimits || {
                  minDuration: 1,
                  maxDuration: 48,
                  maxActiveReservations: 1
                }
              });
            }
            else {
              this.initializing = false
            }
          }
          catch (e) {
            console.log("Error parsing initializeStore items:", e)
            this.initializing = false
          }
        }
      }).catch(() => {
        this.initializing = false
      });
    },

    setAppConfig(config) {
      this.appConfig = { ...this.appConfig, ...config };
      this.configLoaded = true;
      this.configError = false;
      this.configErrorMessage = "";
    },

    setConfigError(errorMessage) {
      this.configError = true;
      this.configErrorMessage = errorMessage;
      this.configLoaded = false;
    },

    clearConfigError() {
      this.configError = false;
      this.configErrorMessage = "";
    },

    setUser(payload) {
      if (!payload.callback) payload.callback = () => { };

      if (!payload.loginToken) return payload.callback({ success: false, message: "loginToken was missing" });
      let _this = this;

      axios({
        method: "get",
        url: AppSettings.APIServer.user.check_token,
        headers: {"Authorization" : `Bearer ${payload.loginToken}`}
      })
      .then(function (response) {
          if (response.data.status == true) {
            _this.user.loginToken = payload.loginToken
            _this.user.email = response.data.data.email
            _this.user.role = response.data.data.role
            _this.user.roles = response.data.data.roles || []
            _this.user.loggedinAt = new Date()
            if (response.data.data.reservationLimits) {
              _this.user.reservationLimits = response.data.data.reservationLimits
            }
            localStorage.setItem("user", JSON.stringify(_this.user))
            if (_this.initializing) _this.initializing = false
            return payload.callback({ success: true, message: "Login token OK!" });
          }
          else {
            console.log("Invalid token - logging user out.")
            _this.logoutUser()
            if (_this.initializing) _this.initializing = false
            return payload.callback({ success: false, message: "Invalid login token." });
          }
      })
      .catch(function (error) {
          if (error.response && error.response.status == 400) {
            return payload.callback({ success: false, message: error.response.data.detail });
          }
          else if (error.response && error.response.status == 401) {
            console.log("Unauthorized - Logging user out.")
            _this.logoutUser()
            if (_this.initializing) _this.initializing = false
            return payload.callback({ success: false, message: "Invalid login token." });
          }
          else {
            console.log(error)
            return payload.callback({ success: false, message: "Unknown error." });
          }
      });
    },

    logoutUser() {
      localStorage.removeItem("user")
      this.user.loginToken = ""
      this.user.email = ""
      this.user.role = ""
      this.user.roles = []
      this.user.loggedinAt = null
    },

    showMessage(payload) {
      this.snackbar.text = payload.text;
      this.snackbar.color = payload.color || "primary";
      this.snackbar.close = payload.close || false;
      this.snackbar.multiline = (payload.text.length > 50) ? true : false;

      if (payload.multiline) {
        this.snackbar.multiline = payload.multiline;
      }

      if (payload.timeout) {
        this.snackbar.timeout = payload.timeout;
      }

      this.snackbar.visible = true;
    },

    closeMessage() {
      this.snackbar.visible = false;
    },

    async loadAppConfig() {
      try {
        const response = await axios.get(AppSettings.APIServer.app.get_config);
        if (response.data.status) {
          this.setAppConfig(response.data.data);
        } else {
          console.error('Failed to load app config:', response.data.message);
          this.setConfigError(response.data.message || 'Failed to load application configuration');
          return;
        }
      } catch (error) {
        console.error('Error loading app config:', error);
        const errorMessage = error.response?.data?.message || error.message || 'Unable to connect to server';
        this.setConfigError(`Error loading app configuration: ${errorMessage}`);
        return;
      }
    }
  }
})
