import dayjs from "dayjs";
var utc = require('dayjs/plugin/utc')
var timezone = require('dayjs/plugin/timezone')
dayjs.extend(utc)
dayjs.extend(timezone)
import { store } from '/src/store/store.js'

/**
 * Returns the given ISO timestamp in application's timezone and parses it in human-readable format.
 * Example return: "04.02.2022 12:23"
 * @param {timestamp} timestamp 
 * @return string
 */
function DisplayTime(timestamp) {
  // Add UTC +0 abbreviation to end of the timestamp if it is already not there
  if (timestamp.slice(-1) !== "Z") timestamp = timestamp + "Z"
  // Parse to current timezone
  let time = dayjs(timestamp).tz(store.getters.appTimezone)
  return time.format("DD.MM.YYYY HH:mm")
}

/**
 * Returns the given ISO timestamp in application's timezone.
 * Example return: ?
 * @param {timestamp} timestamp 
 * @return string
 */
function TimestampToLocalTimeZone(timestamp) {
  // Add UTC +0 abbreviation to end of the timestamp if it is already not there
  if (timestamp.slice(-1) !== "Z") timestamp = timestamp + "Z"
  // Parse to current timezone
  let time = dayjs(timestamp).tz(store.getters.appTimezone)
  return time.toISOString()
}

export { DisplayTime, TimestampToLocalTimeZone }