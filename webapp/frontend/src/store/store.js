/**
 * Main Pinia store for application state management.
 * Holds authentication state, app configuration fetched from the backend,
 * and global UI state (snackbar messages). All components share this single store.
 * @module store
 */

import { defineStore } from 'pinia'
import axios from 'axios'
import AppSettings from '/src/AppSettings.js'
import { initAnalytics, identifyUser, clearUserIdentity } from '/src/plugins/analytics.js'

/**
 * Main application store.
 * @returns {Object} Pinia store instance with state, getters, and actions.
 */
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
    // Confirmation dialog state (global, promise-based)
    confirmDialog: {
      visible: false,
      title: 'Confirm',
      message: '',
      confirmText: 'Yes',
      cancelText: 'Cancel',
      confirmColor: 'primary',
      resolve: null,
    },
    // Prompt dialog state (global, promise-based)
    promptDialog: {
      visible: false,
      title: 'Input',
      message: '',
      inputLabel: '',
      inputType: 'text',
      defaultValue: '',
      min: undefined,
      max: undefined,
      rules: [],
      resolve: null,
    },
    initializing: true,
    // Information about the currently logged-in user
    user: {
      loginToken: "",
      email: "",
      name: "",
      role: "",
      roles: [],
      loggedinAt: null,
      reservationLimits: {
        minDuration: 1,
        maxDuration: 48,
        maxActiveReservations: 1,
        allowLowPriority: true
      },
      startScriptPath: "",
      stopScriptPath: ""
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
      email: {
        enabled: false
      },
      analytics: {
        rybbitUrl: "",
        rybbitSiteId: "",
        googleAnalyticsId: ""
      },
      legal: {
        enabled: false
      },
      features: {
        startScriptsEnabled: true,
        stopScriptsEnabled: true,
        sshKeysEnabled: true,
        startScriptTimeoutSeconds: 40,
        stopScriptTimeoutSeconds: 40
      }
    },
    configLoaded: false,
    configError: false,
    configErrorMessage: ""
  }),

  getters: {
    /** @returns {boolean} Whether a user is currently authenticated. */
    isLoggedIn: (state) => {
      if (state.user && state.user.loginToken) return true
      else return false
    },
    /** @returns {boolean} Whether the store is still performing async initialisation. */
    isInitializing: (state) => state.initializing,
    /** @returns {boolean} Whether loading the backend app configuration failed. */
    hasConfigError: (state) => state.configError,
    /** @returns {string} Display name of the application. */
    appName: (state) => state.appConfig.app.name || 'Containers on the Fly',
    /** @returns {string} IANA timezone string used for all date formatting. */
    appTimezone: (state) => state.appConfig.app.timezone,
    /** @returns {string} Contact email shown to users. */
    contactEmail: (state) => state.appConfig.app.contactEmail,
    /** @returns {string} Instructional text shown on the login page. */
    loginPageInfo: (state) => state.appConfig.instructions.login,
    /** @returns {string} Instructional text shown on the reservation page. */
    reservationPageInstructions: (state) => state.appConfig.instructions.reservation,
    /** @returns {string} Instructional text included in reservation emails. */
    emailInstructions: (state) => state.appConfig.instructions.email,
    /** @returns {string} Custom label for the username input field. */
    usernameField: (state) => state.appConfig.instructions.usernameFieldLabel,
    /** @returns {string} Custom label for the password input field. */
    passwordField: (state) => state.appConfig.instructions.passwordFieldLabel,
    /** @returns {boolean} Whether email notifications are enabled. */
    emailEnabled: (state) => state.appConfig.email?.enabled || false,
    /** @returns {boolean} Whether legal documents (privacy policy, ToS) are enabled. */
    legalEnabled: (state) => state.appConfig.legal?.enabled || false,
    /** @returns {Object} The current user's reservation limit settings. */
    userReservationLimits: (state) => state.user.reservationLimits,
    /** @returns {number} Minimum reservation duration (hours) for the current user. */
    userMinDuration: (state) => state.user.reservationLimits.minDuration,
    /** @returns {number} Maximum reservation duration (hours) for the current user. */
    userMaxDuration: (state) => state.user.reservationLimits.maxDuration,
    /** @returns {number} Maximum concurrent active reservations for the current user. */
    userMaxActiveReservations: (state) => state.user.reservationLimits.maxActiveReservations,
    /** @returns {boolean} Whether the current user is allowed to create low-priority reservations, based on their roles. */
    userAllowLowPriority: (state) => state.user.reservationLimits?.allowLowPriority !== false,
    /** @returns {boolean} Whether start scripts are enabled system-wide. */
    startScriptsEnabled: (state) => state.appConfig.features?.startScriptsEnabled !== false,
    /** @returns {boolean} Whether stop scripts are enabled system-wide. */
    stopScriptsEnabled: (state) => state.appConfig.features?.stopScriptsEnabled !== false,
    /** @returns {boolean} Whether SSH key authentication is enabled system-wide. */
    sshKeysEnabled: (state) => state.appConfig.features?.sshKeysEnabled !== false,
    /** @returns {number} Start script timeout in seconds. */
    startScriptTimeoutSeconds: (state) => state.appConfig.features?.startScriptTimeoutSeconds || 40,
    /** @returns {number} Stop script timeout in seconds. */
    stopScriptTimeoutSeconds: (state) => state.appConfig.features?.stopScriptTimeoutSeconds || 40,
  },

  actions: {
    /**
     * Bootstrap the store on application startup.
     * Loads backend configuration, then restores the user session from
     * localStorage and validates the token against the backend.
     */
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
                "name": user.name || "",
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

    /**
     * Merge fetched backend configuration into the store.
     * @param {Object} config - Configuration object from the `/app/config` endpoint.
     */
    setAppConfig(config) {
      this.appConfig = { ...this.appConfig, ...config };
      this.configLoaded = true;
      this.configError = false;
      this.configErrorMessage = "";
    },

    /**
     * Record that loading the app configuration failed.
     * @param {string} errorMessage - Human-readable error description.
     */
    setConfigError(errorMessage) {
      this.configError = true;
      this.configErrorMessage = errorMessage;
      this.configLoaded = false;
    },

    /**
     * Validate a login token with the backend and persist user state.
     * On success the user's profile (email, role, reservation limits) is
     * saved to both the store and localStorage. On failure the user is logged out.
     * @param {Object} payload - Must contain `loginToken` {string}. May contain
     *   an optional `callback` {Function} invoked with `{success, message}`.
     */
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
            _this.user.name = response.data.data.name || ""
            _this.user.role = response.data.data.role
            _this.user.roles = response.data.data.roles || []
            _this.user.loggedinAt = new Date()
            if (response.data.data.reservationLimits) {
              _this.user.reservationLimits = response.data.data.reservationLimits
            }
            _this.user.startScriptPath = response.data.data.startScriptPath || ""
            _this.user.stopScriptPath = response.data.data.stopScriptPath || ""
            localStorage.setItem("user", JSON.stringify(_this.user))
            identifyUser({ email: _this.user.email, name: _this.user.name })
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

    /** Clear all user state from the store and remove the session from localStorage. */
    logoutUser() {
      clearUserIdentity()
      localStorage.removeItem("user")
      this.user.loginToken = ""
      this.user.email = ""
      this.user.name = ""
      this.user.role = ""
      this.user.roles = []
      this.user.loggedinAt = null
    },

    /**
     * Show a confirmation dialog and return a Promise that resolves to true/false.
     * @param {Object} options
     * @param {string} options.title - Dialog title.
     * @param {string} options.message - Dialog body text.
     * @param {string} [options.confirmText='Yes'] - Confirm button label.
     * @param {string} [options.cancelText='Cancel'] - Cancel button label.
     * @param {string} [options.confirmColor='primary'] - Confirm button color.
     * @returns {Promise<boolean>} true if confirmed, false if cancelled.
     */
    showConfirmDialog(options) {
      return new Promise((resolve) => {
        this.confirmDialog = {
          visible: true,
          title: options.title || 'Confirm',
          message: options.message || '',
          confirmText: options.confirmText || 'Yes',
          cancelText: options.cancelText || 'Cancel',
          confirmColor: options.confirmColor || 'primary',
          resolve,
        }
      })
    },

    /**
     * Resolve the confirm dialog Promise and close it.
     * @param {boolean} result - Whether the user confirmed.
     */
    resolveConfirmDialog(result) {
      if (this.confirmDialog.resolve) {
        this.confirmDialog.resolve(result)
      }
      this.confirmDialog.visible = false
      this.confirmDialog.resolve = null
    },

    /**
     * Show a prompt dialog and return a Promise that resolves to the input string or null.
     * @param {Object} options
     * @param {string} options.title - Dialog title.
     * @param {string} [options.message] - Optional instructional text.
     * @param {string} [options.inputLabel] - Text field label.
     * @param {string} [options.inputType='text'] - Input type (text, number).
     * @param {string} [options.defaultValue=''] - Pre-filled value.
     * @param {Array} [options.rules=[]] - Vuetify validation rules for the text field.
     * @returns {Promise<string|null>} The input string, or null if cancelled.
     */
    showPromptDialog(options) {
      return new Promise((resolve) => {
        this.promptDialog = {
          visible: true,
          title: options.title || 'Input',
          message: options.message || '',
          inputLabel: options.inputLabel || '',
          inputType: options.inputType || 'text',
          defaultValue: options.defaultValue != null ? options.defaultValue : '',
          min: options.min,
          max: options.max,
          rules: options.rules || [],
          resolve,
        }
      })
    },

    /**
     * Resolve the prompt dialog Promise and close it.
     * @param {string|null} result - The entered text, or null if cancelled.
     */
    resolvePromptDialog(result) {
      if (this.promptDialog.resolve) {
        this.promptDialog.resolve(result)
      }
      this.promptDialog.visible = false
      this.promptDialog.resolve = null
    },

    /**
     * Display a global snackbar notification.
     * @param {Object} payload
     * @param {string} payload.text - Message text to display.
     * @param {string} [payload.color="primary"] - Vuetify color string.
     * @param {boolean} [payload.close=false] - Whether to show a close button.
     * @param {boolean} [payload.multiline] - Force multiline layout (auto-detected if text > 50 chars).
     * @param {number} [payload.timeout] - Auto-dismiss timeout in milliseconds.
     */
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

    /** Hide the global snackbar notification. */
    closeMessage() {
      this.snackbar.visible = false;
    },

    /**
     * Fetch application configuration from the backend `/app/config` endpoint.
     * On success, merges the config into the store via `setAppConfig`.
     * On failure, records the error via `setConfigError`.
     * @returns {Promise<void>}
     */
    async loadAppConfig() {
      try {
        const response = await axios.get(AppSettings.APIServer.app.get_config);
        if (response.data.status) {
          this.setAppConfig(response.data.data);
          initAnalytics(response.data.data.analytics);
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
