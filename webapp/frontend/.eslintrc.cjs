module.exports = {
  root: true,
  env: {
    node: true
  },
  'extends': [
    'plugin:vue/vue3-essential',
    'eslint:recommended'
  ],
  rules: {
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'vue/valid-v-slot': ['error', {
      allowModifiers: true,
    }],
  },
  overrides: [
    {
      files: ['src/**/*.vue'],
      rules: {
        'vue/multi-word-component-names': 0,
      }
    }
  ]
}
