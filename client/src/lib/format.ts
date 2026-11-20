/**
 * Display locale for numbers, money and dates. Follows the user's saved
 * preference (Settings), else the browser. Set once by PreferencesSync.
 */
let locale: string | undefined

export function setDisplayLocale(next?: string | null) {
  locale = next || undefined
  if (typeof document !== "undefined" && next) document.documentElement.lang = next
}

export function displayLocale() {
  return locale
}
