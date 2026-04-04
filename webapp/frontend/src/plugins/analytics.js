/**
 * Optional analytics integrations (Rybbit and Google Analytics).
 * Both services are activated only when their configuration values are
 * provided via the app config endpoint. All exported functions are safe
 * no-ops when the corresponding service is not configured.
 * @module plugins/analytics
 */

let analyticsConfig = {}

/**
 * Check that a URL string uses http: or https: protocol.
 * @param {string} url - URL to validate.
 * @returns {boolean} True if the URL is safe to load as a script source.
 */
function isSafeUrl(url) {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'https:' || parsed.protocol === 'http:'
  } catch {
    return false
  }
}

/**
 * Inject a <script> tag into document.head if not already present.
 * Only allows http/https URLs to prevent script injection.
 * @param {string} src - Script URL.
 * @param {Object} [attrs] - Additional attributes to set on the element.
 * @returns {Promise<void>} Resolves when the script loads.
 */
function loadScript(src, attrs = {}) {
  if (!isSafeUrl(src)) {
    return Promise.reject(new Error(`Refused to load script with unsafe URL: ${src}`))
  }

  // Avoid duplicate injection
  const existing = Array.from(document.querySelectorAll('script[src]'))
    .some(s => s.getAttribute('src') === src)
  if (existing) {
    return Promise.resolve()
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = src
    script.async = true
    for (const [key, value] of Object.entries(attrs)) {
      script.setAttribute(key, value)
    }
    script.onload = resolve
    script.onerror = () => reject(new Error(`Failed to load analytics script: ${src}`))
    document.head.appendChild(script)
  })
}

/**
 * Initialise Rybbit analytics if rybbitUrl and rybbitSiteId are configured.
 * Rybbit auto-tracks page views including SPA navigation.
 */
function initRybbit() {
  if (!analyticsConfig.rybbitUrl || !analyticsConfig.rybbitSiteId) return

  if (!isSafeUrl(analyticsConfig.rybbitUrl)) {
    console.warn('Rybbit analytics URL is not a valid http/https URL, skipping.')
    return
  }

  loadScript(`${analyticsConfig.rybbitUrl}/api/script.js`, {
    'data-site-id': analyticsConfig.rybbitSiteId
  }).catch(err => console.warn('Rybbit analytics failed to load:', err.message))
}

/**
 * Initialise Google Analytics if googleAnalyticsId is configured.
 * Validates that the measurement ID matches the expected GA4 format.
 */
function initGoogleAnalytics() {
  if (!analyticsConfig.googleAnalyticsId) return

  const gaId = analyticsConfig.googleAnalyticsId

  if (!/^G-[A-Za-z0-9]+$/.test(gaId)) {
    console.warn('Google Analytics ID does not match expected format (G-XXXXXXXXXX), skipping.')
    return
  }

  loadScript(`https://www.googletagmanager.com/gtag/js?id=${gaId}`)
    .then(() => {
      window.dataLayer = window.dataLayer || []
      window.gtag = function () { window.dataLayer.push(arguments) }
      window.gtag('js', new Date())
      window.gtag('config', gaId)
    })
    .catch(err => console.warn('Google Analytics failed to load:', err.message))
}

/**
 * Generate a simple hash string from an input using SHA-256.
 * Falls back to a basic hash if SubtleCrypto is unavailable.
 * @param {string} input - String to hash.
 * @returns {Promise<string>} Hex-encoded hash.
 */
async function hashString(input) {
  if (window.crypto && window.crypto.subtle) {
    const data = new TextEncoder().encode(input)
    const buffer = await window.crypto.subtle.digest('SHA-256', data)
    return Array.from(new Uint8Array(buffer)).map(b => b.toString(16).padStart(2, '0')).join('')
  }
  // Fallback: simple djb2 hash (non-cryptographic, but avoids sending raw PII)
  let hash = 5381
  for (let i = 0; i < input.length; i++) {
    hash = ((hash << 5) + hash) + input.charCodeAt(i)
  }
  return Math.abs(hash).toString(16)
}

/**
 * Bootstrap all configured analytics services.
 * Call from the store after app config is loaded.
 * @param {Object} config - Analytics config from /app/config response.
 * @param {string} config.rybbitUrl - Rybbit instance URL.
 * @param {string} config.rybbitSiteId - Rybbit site ID.
 * @param {string} config.googleAnalyticsId - GA4 measurement ID.
 */
export function initAnalytics(config) {
  if (!config) return
  analyticsConfig = config
  initRybbit()
  initGoogleAnalytics()
}

/**
 * Identify a logged-in user across all active analytics services.
 * Rybbit receives raw user data (typically self-hosted, privacy-friendly).
 * Google Analytics receives a hashed user ID to comply with Google's
 * PII policy -- raw email/name are not sent to GA.
 * @param {Object} user
 * @param {string} user.email - User email.
 * @param {string} user.name - User display name.
 */
export function identifyUser(user) {
  if (!user || !user.email) return

  // Rybbit - send full user data (self-hosted / privacy-friendly service)
  if (window.rybbit && analyticsConfig.rybbitSiteId) {
    window.rybbit.identify(user.email, { name: user.name, email: user.email })
  }

  // Google Analytics - use hashed ID only (Google ToS prohibits raw PII)
  if (window.gtag && analyticsConfig.googleAnalyticsId) {
    hashString(user.email).then(hashedId => {
      window.gtag('config', analyticsConfig.googleAnalyticsId, { user_id: hashedId })
    })
  }
}

/**
 * Clear user identity from all active analytics services.
 * Called on logout.
 */
export function clearUserIdentity() {
  // Rybbit
  if (window.rybbit) {
    window.rybbit.clearUserId()
  }

  // Google Analytics
  if (window.gtag && analyticsConfig.googleAnalyticsId) {
    window.gtag('config', analyticsConfig.googleAnalyticsId, { user_id: null })
  }
}
