/**
 * Copy text to clipboard with fallback for HTTP (non-secure) contexts.
 * navigator.clipboard requires HTTPS; falls back to execCommand for HTTP.
 * @param {string} text - The text to copy
 * @returns {Promise<boolean>} True if copy succeeded, false otherwise
 */
export function copyToClipboard(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text).then(() => true).catch(() => false)
  }

  // Fallback for HTTP contexts
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  try {
    document.execCommand('copy')
    document.body.removeChild(textarea)
    return Promise.resolve(true)
  } catch {
    document.body.removeChild(textarea)
    return Promise.resolve(false)
  }
}
