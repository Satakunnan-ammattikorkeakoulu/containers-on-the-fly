/**
 * Returns a Vuetify color string for an audit log action.
 * @param {string} action - The audit log action name
 * @returns {string} Vuetify color name
 */
export function getActionColor(action) {
  if (!action) return 'grey';
  if (action.startsWith('LOGIN_FAILED')) return 'red';
  if (action.startsWith('LOGIN')) return 'blue';
  if (action.startsWith('RESERVATION')) return 'green';
  if (action.startsWith('USER')) return 'orange';
  if (action.startsWith('ROLE')) return 'purple';
  if (action.startsWith('CONTAINER')) return 'teal';
  if (action.startsWith('COMPUTER')) return 'indigo';
  if (action.startsWith('SETTINGS')) return 'grey';
  return 'grey';
}
