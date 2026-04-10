/**
 * Returns a Vuetify color string for an audit log action chip.
 *
 * Reservation actions get fine-grained semantic colors:
 *   - green for creation / start / resume / extend / successful restart
 *   - warning (yellow) for low-priority pause
 *   - red for cancel / auto-stop / error / failed restart
 *   - blue for neutral edits (description updates, admin end-time edits)
 *
 * Non-reservation actions fall back to a broad category color based on
 * the action prefix.
 *
 * @param {string} action - The audit log action name.
 * @param {object} [details] - Optional audit log details for finer-grained
 *     coloring (e.g. RESERVATION_RESTART with success=false becomes red).
 * @returns {string} Vuetify color name.
 */
export function getActionColor(action, details) {
  if (!action || typeof action !== 'string') return 'grey';
  const d = (details && typeof details === 'object') ? details : {};

  switch (action) {
    case 'RESERVATION_CREATE':
    case 'RESERVATION_EXTEND':
    case 'RESERVATION_STARTED':
    case 'RESERVATION_RESUMED':
      return 'green';
    case 'RESERVATION_RESTART':
      return d.success === false ? 'red' : 'green';
    case 'RESERVATION_PAUSED':
      return 'warning';
    case 'RESERVATION_CANCEL':
    case 'RESERVATION_AUTO_STOPPED':
    case 'RESERVATION_ERROR':
      return 'red';
    case 'RESERVATION_UPDATE_DESCRIPTION':
    case 'RESERVATION_ADMIN_EDIT':
      return 'blue';
  }

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

/**
 * Convert an UPPER_SNAKE_CASE action constant into a fallback
 * human-readable string. Used when the formatter has no specific
 * rule for the given action.
 * @param {string} action
 * @returns {string}
 */
function prettifyActionFallback(action) {
  if (!action || typeof action !== 'string') return 'Unknown event';
  const cleaned = action.replace(/_/g, ' ').toLowerCase().trim();
  if (!cleaned) return 'Unknown event';
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

/**
 * Format an audit log action (plus optional details dict) into a
 * friendly past-tense label for the user activity feed.
 *
 * Always returns a non-empty string. If anything about `action` or
 * `details` is unexpected, falls back to a prettified version of the
 * action constant so the row never renders blank.
 *
 * @param {string} action - The audit log action constant.
 * @param {object} [details] - Optional whitelist of detail fields.
 * @returns {string} Human-readable label.
 */
export function formatActionLabel(action, details) {
  try {
    if (!action || typeof action !== 'string') return 'Unknown event';
    const d = (details && typeof details === 'object') ? details : {};

    switch (action) {
      case 'RESERVATION_CREATE':
        return 'Reservation created';
      case 'RESERVATION_EXTEND': {
        const hours = Number(d.duration);
        if (Number.isFinite(hours) && hours > 0) {
          return `Reservation extended by ${hours} ${hours === 1 ? 'hour' : 'hours'}`;
        }
        return 'Reservation extended';
      }
      case 'RESERVATION_UPDATE_DESCRIPTION':
        return 'Reservation description updated';
      case 'RESERVATION_CANCEL':
        if (d.cancelledBy === 'admin') return 'Reservation cancelled by admin';
        if (d.cancelledBy === 'user') return 'Reservation cancelled by you';
        return 'Reservation cancelled';
      case 'RESERVATION_ADMIN_EDIT':
        return 'End time changed by admin';
      case 'RESERVATION_AUTO_STOPPED':
        return 'Reservation ended (time ran out)';
      case 'RESERVATION_STARTED':
        return d.isLowPriority ? 'Low-priority container started' : 'Container started';
      case 'RESERVATION_RESUMED':
        return 'Low-priority container resumed';
      case 'RESERVATION_PAUSED':
        return 'Low-priority container paused';
      case 'RESERVATION_RESTART':
        if (d.success === false) return 'Container restart failed';
        return 'Container restarted';
      case 'RESERVATION_ERROR':
        if (d.resumeFailure) return 'Low-priority container failed to resume';
        return 'Container failed to start';
      default:
        return prettifyActionFallback(action);
    }
  } catch {
    return prettifyActionFallback(action);
  }
}
