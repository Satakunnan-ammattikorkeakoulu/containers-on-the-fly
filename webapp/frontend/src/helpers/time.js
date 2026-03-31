/**
 * Date/time formatting utilities.
 * All date handling in the frontend must go through these helpers so that
 * timestamps are consistently converted to the application-configured timezone.
 * Uses Day.js with UTC and timezone plugins.
 * @module helpers/time
 */

import dayjs from "dayjs";
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
dayjs.extend(utc)
dayjs.extend(timezone)
import { useMainStore } from '/src/store/store.js'

/**
 * Format an ISO timestamp as a human-readable string in the app's timezone.
 * @param {string} timestamp - ISO 8601 timestamp (with or without trailing "Z").
 * @returns {string} Formatted date string, e.g. "04.02.2022 12:23".
 */
function DisplayTime(timestamp) {
  const store = useMainStore()
  // Add UTC +0 abbreviation to end of the timestamp if it is already not there
  if (timestamp.slice(-1) !== "Z") timestamp = timestamp + "Z"
  // Parse to current timezone
  let time = dayjs(timestamp).tz(store.appTimezone)
  return time.format("DD.MM.YYYY HH:mm")
}

/**
 * Convert an ISO timestamp to an ISO string in the application's timezone.
 * Useful when the backend returns UTC timestamps that need to be shifted
 * before being sent to date-picker components or compared locally.
 * @param {string} timestamp - ISO 8601 timestamp (with or without trailing "Z").
 * @returns {string} ISO 8601 string adjusted to the app's configured timezone.
 */
function TimestampToLocalTimeZone(timestamp) {
  const store = useMainStore()
  // Add UTC +0 abbreviation to end of the timestamp if it is already not there
  if (timestamp.slice(-1) !== "Z") timestamp = timestamp + "Z"
  // Parse to current timezone
  let time = dayjs(timestamp).tz(store.appTimezone)
  return time.toISOString()
}

export { DisplayTime, TimestampToLocalTimeZone }
