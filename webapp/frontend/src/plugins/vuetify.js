/**
 * Vuetify plugin configuration.
 * Initialises Vuetify 3 with the dark theme and Material Design Icons.
 * @module plugins/vuetify
 */

import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import '@mdi/font/css/materialdesignicons.css'

export default createVuetify({
  theme: {
    defaultTheme: 'dark',
  },
  defaults: {
    VTextField: {
      variant: 'outlined',
      persistentHint: true,
    },
    VTextarea: {
      variant: 'outlined',
      persistentHint: true,
    },
    VSelect: {
      variant: 'outlined',
      persistentHint: true,
    },
    VSwitch: {
      persistentHint: true,
    },
  },
})
