<template>
  <v-row class="fill-height">
    <v-col>
      <v-sheet height="64">
        <v-toolbar flat>
          <v-btn variant="flat" class="mr-4" color="#424242" @click="setToday">
            Today
          </v-btn>
          <v-btn fab variant="text" size="small" color="grey darken-2" @click="prev">
            <v-icon size="small">
              mdi-chevron-left
            </v-icon>
          </v-btn>
          <v-btn fab variant="text" size="small" color="grey darken-2" @click="next">
            <v-icon size="small">
              mdi-chevron-right
            </v-icon>
          </v-btn>
          <v-select
            v-model="type"
            :items="types"
            dense
            outlined
            hide-details
            class="ma-2"
            label="type"
          ></v-select>
          <v-btn-toggle
            v-model="viewMode"
            mandatory
            dense
            class="ma-2 availability-toggle"
            color="primary"
          >
            <v-btn size="small" value="reservations" variant="flat" :color="viewMode === 'reservations' ? 'primary' : '#424242'">
              <v-icon size="small">mdi-calendar-clock</v-icon>
              Reservations
            </v-btn>
            <v-btn size="small" value="availability" variant="flat" :color="viewMode === 'availability' ? 'primary' : '#424242'">
              <v-icon size="small">mdi-server</v-icon>
              Availability
            </v-btn>
          </v-btn-toggle>
          <v-btn
            size="small"
            variant="flat"
            color="#424242"
            class="ma-2"
            @click="refreshCalendarData"
          >
            <v-icon size="small" left>mdi-refresh</v-icon>
            Refresh
          </v-btn>
          <v-spacer></v-spacer>
          <v-toolbar-title v-if="$refs.calendar">
            {{ $refs.calendar.title }}
          </v-toolbar-title>
        </v-toolbar>
      </v-sheet>
      <v-sheet height="600" class="calendar-sheet">
        <v-calendar
          ref="calendar"
          v-model="focus"
          color="primary"
          :events="events"
          :event-color="getEventColor"
          :type="type"
          :weekdays="weekdays"
          :first-day-of-week="1"
          @click:time="selectSlot"
          event-overlap-mode="column"
          first-interval="0"
          interval-minutes="30"
          interval-count="48"
          :interval-format="intervalFormat"
        >
          <template #event="event">
            <v-tooltip location="top" open-delay="150" max-width="320" content-class="calendar-event-tooltip">
              <template v-slot:activator="{ props }">
                <div
                  v-bind="props"
                  :class="event.eventParsed.input.type === 'availability' ? 'availability-event-content' : 'reservation-event-content'"
                >
                  <template v-if="event.eventParsed.input.type === 'availability'">
                    <div class="server-header">
                      <strong>{{event.eventParsed.input.computerName}}</strong>
                    </div>
                    <div class="resource-list" v-html="formatResourcesWithIndicators(event.eventParsed.input)" />
                  </template>
                  <template v-else>
                    <p><b>{{event.eventParsed.input.name}}</b></p>
                    <p v-if="event.eventParsed.input.isLowPriority" class="low-priority-label">Low-Priority</p>
                    <p v-html="getReservationSpecs(event.eventParsed.input.reservationId)" />
                  </template>
                </div>
              </template>
              <div class="calendar-tooltip-content">
                <template v-if="event.eventParsed.input.type === 'availability'">
                  <div style="font-weight: bold; margin-bottom: 4px;">{{event.eventParsed.input.computerName}}</div>
                  <div v-html="formatResourcesWithIndicators(event.eventParsed.input)" />
                </template>
                <template v-else>
                  <div style="font-weight: bold; margin-bottom: 4px;">{{event.eventParsed.input.name}}</div>
                  <div v-if="event.eventParsed.input.isLowPriority" class="low-priority-label" style="margin-bottom: 4px;">Low-Priority</div>
                  <div v-html="getReservationSpecs(event.eventParsed.input.reservationId)" />
                </template>
              </div>
            </v-tooltip>
          </template>
        </v-calendar>
        <v-menu v-model="selectedOpen" :close-on-content-click="false" :activator="selectedElement" offset-x>
          <v-card color="grey lighten-4" min-width="320px" flat>
            <v-toolbar :color="selectedEvent.color" dark>
              <v-btn icon>
                <v-icon>mdi-pencil</v-icon>
              </v-btn>
              <v-toolbar-title><span v-html="selectedEvent.name"></span></v-toolbar-title>
              <v-spacer></v-spacer>
              <v-btn icon>
                <v-icon>mdi-heart</v-icon>
              </v-btn>
              <v-btn icon>
                <v-icon>mdi-dots-vertical</v-icon>
              </v-btn>
            </v-toolbar>
            <v-card-text>
              <span v-html="selectedEvent.details"></span>
            </v-card-text>
            <v-card-actions>
              <v-btn variant="text" color="secondary" @click="selectedOpen = false">
                Cancel
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-menu>
      </v-sheet>
    </v-col>
  </v-row>
</template>

<script>
  /**
   * Interactive calendar displaying reservations and server resource availability.
   * Supports month/week/day/4-day views and toggles between a reservation timeline
   * and a per-server availability heatmap with color-coded resource indicators.
   * Emits "slotSelected" when a user clicks a future time slot to start a new reservation.
   */
  import { TimestampToLocalTimeZone } from '/src/helpers/time.js'
  import dayjs from "dayjs";
  import axios from 'axios';
  import utc from 'dayjs/plugin/utc'
  import timezone from 'dayjs/plugin/timezone'
  import isoWeek from 'dayjs/plugin/isoWeek'
  dayjs.extend(utc)
  import customParseFormat from 'dayjs/plugin/customParseFormat'
  dayjs.extend(timezone)
  dayjs.extend(customParseFormat)
  dayjs.extend(isoWeek)
  import { useMainStore } from '@/store/store'

  export default {
    name: 'CalendarReservations',
    setup() {
      const store = useMainStore()
      return { store }
    },
    props: {
      propReservations: {
        type: Array,
        required: true
      },
      readOnly: {
        type: Boolean,
        default: false
      },
    },
    data: () => ({
      focus: '',
      type: 'week',
      types: ['month', 'week', 'day', '4day'],
      weekdays: [1,2,3,4,5,6,0],
      typeToLabel: {
        month: 'Month',
        week: 'Week',
        day: 'Day',
      },
      selectedEvent: {},
      selectedElement: null,
      selectedOpen: false,
      events: [],
      viewMode: 'reservations',
      availabilityEvents: [],
      colors: ['red', 'pink', 'purple', 'deep-purple', 'indigo', 'blue',
               'light-blue', 'cyan', 'teal', 'green', 'light-green darken-1',
               'lime darken-2', 'yellow darken-3', 'amber darken-2', 'orange darken-3', 'deep-orange', 'brown', 'grey', 'blue-grey'],
      reservationColorMap: {},
      nowIndicatorInterval: null,
    }),
    computed: {
      /** Only draw the "now" line on time-grid views (not month). */
      showNowLine() {
        return this.type !== 'month'
      },
    },
    mounted () {
      if (this.$refs.calendar) {
        this.$refs.calendar.checkChange()
      }
      this.$nextTick(() => {
        this.updateNowLine()
        this.scrollToNow()
      })
      // Refresh displayed events and the "now" indicator line each minute.
      this.nowIndicatorInterval = setInterval(() => {
        this.updateDisplayedEvents()
        this.updateNowLine()
      }, 60000)
    },
    beforeUnmount() {
      if (this.nowIndicatorInterval) {
        clearInterval(this.nowIndicatorInterval)
      }
    },
    methods: {
      intervalFormat(interval) {
        return interval.time
      },
      /**
       * Handles calendar time-slot clicks. Rounds the selected time down to the
       * nearest 30-minute boundary and emits "slotSelected" if the time is in the future.
       */
      selectSlot( nativeEvent, data ) {
        // If calendar is in read-only mode, don't allow slot selection
        if (this.readOnly) {
          return
        }

        // Only allow time selection in day, week, or 4day views (not month view)
        if (this.type === 'month') {
          this.store.showMessage({ text: "Switch to week, day, or 4-day view to select a specific time.", color: "info" })
          return
        }

        let now = dayjs()
        // Vuetify 4: @click:time passes (nativeEvent, timestampData)
        // timestampData has { date: "YYYY-MM-DD", time: "HH:mm", year, month, day, hour, minute, ... }
        let selectedTime
        if (data && data.date && data.time) {
          selectedTime = dayjs(data.date + " " + data.time)
        } else if (data && data.date) {
          selectedTime = dayjs(data.date)
        } else {
          return
        }
        // Round to nearest 30 minutes (down)
        if (selectedTime.get("minutes") < 30)
          selectedTime = selectedTime.set("minute", 0)
        else
          selectedTime = selectedTime.set("minute", 30)

        // Check that reservation is not made into past
        if (selectedTime < now) {
          this.store.showMessage({ text: "Can only make reservations into future.", color: "red" })
          return
        }

        this.$emit("slotSelected", selectedTime)
      },
      getReservationSpecs( reservationId ) {
        let returnData = ""
        this.propReservations.forEach((res) => {
          if (res.reservationId == reservationId) {
            returnData += res.computerName + "<br>"
            res.hardwareSpecs.forEach((spec) => {
              returnData += spec.amount + " " + spec.format + "<br>"
            })
          }
        })
        return returnData
      },
      /**
       * Builds HTML for per-resource availability indicators (green/yellow/red dots)
       * based on the ratio of available vs. maximum for each hardware spec.
       */
      formatResourcesWithIndicators(availabilityEvent) {
        if (!availabilityEvent.availableSpecs) {
          return availabilityEvent.resourceText
        }
        
        let html = ''
        const specs = availabilityEvent.availableSpecs
        
        // Sort specs alphabetically by type for consistent display order
        const sortedSpecs = Object.values(specs).sort((a, b) => a.type.localeCompare(b.type))
        
        sortedSpecs.forEach(spec => {
          // Calculate availability ratio for this specific resource
          const ratio = spec.available / Math.max(spec.maximum, 1)
          let indicatorClass = 'resource-low'
          if (ratio > 0.75) indicatorClass = 'resource-high'
          else if (ratio > 0.25) indicatorClass = 'resource-medium'
          
          let displayText
          if (spec.type.toLowerCase() === 'gpu' || spec.type.toLowerCase() === 'gpus') {
            displayText = `GPU: ${Math.round(spec.available)}/${Math.round(spec.maximum)}`
          } else if (spec.type.toLowerCase() === 'cpu' || spec.type.toLowerCase() === 'cpus') {
            displayText = `CPU: ${Math.round(spec.available)}/${Math.round(spec.maximum)}`
          } else if (spec.type.toLowerCase() === 'ram') {
            displayText = `RAM: ${Math.round(spec.available)}/${Math.round(spec.maximum)}`
          } else {
            displayText = `${spec.type.toUpperCase()}: ${Math.round(spec.available)}/${Math.round(spec.maximum)}`
          }
          
          html += `<div class="resource-item" style="display: flex; align-items: center; margin: 2px 0;">
            <span class="resource-indicator ${indicatorClass}" style="width: 10px; height: 10px; background-color: ${indicatorClass === 'resource-high' ? '#4CAF50' : indicatorClass === 'resource-medium' ? '#FF9800' : '#F44336'}; border-radius: 50%; display: inline-block; margin-right: 4px; flex-shrink: 0;"></span>
            <span class="resource-text" style="font-size: 11px; color: rgba(255, 255, 255, 0.95);">${displayText}</span>
          </div>`
        })
        
        return html
      },
      viewDay ({ date }) {
        this.focus = date
        this.type = 'day'
      },
      getEventColor (event) {
        return event.color
      },
      setToday () {
        this.focus = ''
      },
      prev () {
        this.$refs.calendar.prev()
      },
      next () {
        this.$refs.calendar.next()
      },
      rnd (a, b) {
        return Math.floor((b - a + 1) * Math.random()) + a
      },
      /** Fetches server availability data for the currently visible calendar date range. */
      async fetchAvailabilityData() {
        if (this.viewMode !== 'availability') {
          return
        }
        
        // Calculate date range for current calendar view based on type
        let calendarStart, calendarEnd;
        
        // Get the current focus date from the calendar
        const focusDate = this.focus ? dayjs(this.focus) : dayjs();
        
        // Calculate range based on calendar type
        switch (this.type) {
          case 'month':
            calendarStart = focusDate.startOf('month');
            calendarEnd = focusDate.endOf('month').add(1, 'day');
            break;
          case 'week':
            // Use isoWeek to ensure Monday is the first day of the week
            calendarStart = focusDate.startOf('isoWeek');
            calendarEnd = focusDate.endOf('isoWeek').add(1, 'day');
            break;
          case '4day':
            // 4-day view shows current day + 3 more days
            calendarStart = focusDate.startOf('day');
            calendarEnd = focusDate.add(3, 'days').endOf('day').add(1, 'day');
            break;
          case 'day':
          default:
            calendarStart = focusDate.startOf('day');
            calendarEnd = focusDate.endOf('day').add(1, 'day');
            break;
        }
        
        
        try {
          const response = await axios({
            method: "get",
            url: "/api/reservation/get_availability_timeline",
            headers: {"Authorization" : `Bearer ${this.store.user.loginToken}`},
            params: {
              startDate: calendarStart.format('YYYY-MM-DD HH:mm:ss'),
              endDate: calendarEnd.format('YYYY-MM-DD HH:mm:ss')
            }
          })
          
          if (response.data.status) {
            this.availabilityEvents = response.data.data.events.map((event, index) => ({
              id: `availability-${event.computerId}-${index}`,
              name: event.name,
              start: new Date(event.start),
              end: new Date(event.end),
              color: event.color,
              timed: event.timed,
              type: event.type,
              computerId: event.computerId,
              computerName: event.computerName,
              availabilityLevel: event.availabilityLevel,
              resourceText: event.resourceText,
              availableSpecs: event.availableSpecs
            }))
            this.updateDisplayedEvents()
          }
        } catch (error) {
          console.error('Error fetching availability data:', error)
          this.store.showMessage({ text: "Error loading availability data.", color: "red" })
        }
      },
      /** Fetches all reservations for the visible date range and emits them to the parent. */
      async fetchAllReservationsForCalendar() {
        // Calculate date range for current calendar view based on type
        let calendarStart, calendarEnd;
        
        // Get the current focus date from the calendar
        const focusDate = this.focus ? dayjs(this.focus) : dayjs();
        
        // Calculate range based on calendar type
        switch (this.type) {
          case 'month':
            calendarStart = focusDate.startOf('month');
            calendarEnd = focusDate.endOf('month').add(1, 'day');
            break;
          case 'week':
            // Use isoWeek to ensure Monday is the first day of the week
            calendarStart = focusDate.startOf('isoWeek');
            calendarEnd = focusDate.endOf('isoWeek').add(1, 'day');
            break;
          case '4day':
            calendarStart = focusDate.startOf('day');
            calendarEnd = focusDate.add(3, 'days').endOf('day').add(1, 'day');
            break;
          case 'day':
          default:
            calendarStart = focusDate.startOf('day');
            calendarEnd = focusDate.endOf('day').add(1, 'day');
            break;
        }
        
        try {
          const response = await axios({
            method: "get",
            url: "/api/reservation/get_all_reservations_for_calendar",
            headers: {"Authorization" : `Bearer ${this.store.user.loginToken}`},
            params: {
              startDate: calendarStart.format('YYYY-MM-DD HH:mm:ss'),
              endDate: calendarEnd.format('YYYY-MM-DD HH:mm:ss')
            }
          })
          
          if (response.data.status) {
            // Emit this data to the parent component so it can update propReservations
            this.$emit('reservationsRefreshed', response.data.data.reservations)
            // If we're in availability mode, also refresh availability data
            if (this.viewMode === 'availability') {
              await this.fetchAvailabilityData()
            }
          }
        } catch (error) {
          console.error('Error fetching all reservations:', error)
          this.store.showMessage({ text: "Error refreshing reservations.", color: "red" })
        }
      },
      /**
       * Inserts or repositions a "now" indicator line inside the calendar's
       * scrollable pane so it scrolls together with the time grid. Called on
       * mount, on each minute tick, and when the view type/focus changes.
       */
      updateNowLine() {
        this.$nextTick(() => {
          const calEl = this.$refs.calendar?.$el
          if (!calEl) return
          const pane = calEl.querySelector('.v-calendar-daily__pane, [class*="__pane"]')

          // Clean up when switching to month view or any state that hides the line.
          if (!this.showNowLine || !pane) {
            const existing = calEl.querySelector('.now-line')
            if (existing) existing.remove()
            return
          }

          // Ensure the pane can host an absolutely-positioned child.
          const paneStyle = window.getComputedStyle(pane)
          if (paneStyle.position === 'static') pane.style.position = 'relative'

          let line = pane.querySelector('.now-line')
          if (!line) {
            line = document.createElement('div')
            line.className = 'now-line'
            pane.appendChild(line)
          }

          const now = new Date()
          const minutesFromMidnight = now.getHours() * 60 + now.getMinutes() + now.getSeconds() / 60
          const fraction = minutesFromMidnight / 1440
          line.style.top = (pane.offsetHeight * fraction) + 'px'
        })
      },
      /** Scrolls the calendar so the previous 30-min mark is near the top on open. */
      scrollToNow() {
        if (!this.showNowLine) return
        this.$nextTick(() => {
          const cal = this.$refs.calendar
          if (!cal) return
          const now = new Date()
          const alignedMinute = now.getMinutes() - (now.getMinutes() % 30)
          const hh = String(now.getHours()).padStart(2, '0')
          const mm = String(alignedMinute).padStart(2, '0')
          if (typeof cal.scrollToTime === 'function') {
            cal.scrollToTime(`${hh}:${mm}`)
          }
          // Nudge upward so the aligned mark has a little breathing room above.
          // scrollAreaRef is the scrollable pane; Vuetify may expose it as a ref object.
          requestAnimationFrame(() => {
            const rawRef = cal.scrollAreaRef
            const pane = rawRef && rawRef.value !== undefined ? rawRef.value : rawRef
            const target = pane && pane.scrollTop !== undefined
              ? pane
              : cal.$el.querySelector('.v-calendar-daily__scroll-area, [class*="scroll-area"]')
            if (target && target.scrollTop >= 10) {
              target.scrollTop -= 10
            }
          })
        })
      },
      /** Switches the calendar events array between reservation and availability data based on viewMode. */
      updateDisplayedEvents() {
        if (this.viewMode === 'availability') {
          this.events = [...this.availabilityEvents]
        } else {
          // Show reservation events
          let events = []
          this.propReservations.forEach((res) => {
            // Use consistent color for each reservation based on ID
            if (!this.reservationColorMap[res.reservationId]) {
              this.reservationColorMap[res.reservationId] = this.colors[res.reservationId % this.colors.length]
            }
            let color = this.reservationColorMap[res.reservationId]

            const startDate = dayjs(TimestampToLocalTimeZone(res.startDate))
            const endDate = dayjs(TimestampToLocalTimeZone(res.endDate))


            const eventData = {
              id: `reservation-${res.reservationId}`,
              name: "Reservation #" + res.reservationId,
              reservationId: res.reservationId,
              isLowPriority: res.isLowPriority,
              start: startDate.toDate(),
              end: endDate.toDate(),
              color: res.isLowPriority ? 'amber darken-2' : color,
              timed: true,
            }
            events.push(eventData)
          })
          this.events = events
        }
      },
      // Method to be called by parent component for refresh
      async refreshCalendarData() {
        // Don't fetch all reservations - just ask parent to refresh
        this.$emit('requestRefresh')
      },
    },
    watch: {
      propReservations: {
        immediate: true,
        handler () {
          this.updateDisplayedEvents()
        }
      },
      viewMode: {
        immediate: true,
        handler (newMode) {
          if (newMode === 'availability') {
            // Use nextTick to ensure calendar is ready
            this.$nextTick(() => {
              this.fetchAvailabilityData()
            })
          } else {
            this.updateDisplayedEvents()
          }
        }
      },
      focus: {
        handler () {
          // Refetch availability data when calendar navigation changes
          this.$nextTick(() => {
            if (this.viewMode === 'availability') {
              this.fetchAvailabilityData()
            }
            this.updateNowLine()
          })
        }
      },
      type: {
        handler () {
          // Refetch availability data when calendar type changes
          this.$nextTick(() => {
            if (this.viewMode === 'availability') {
              this.fetchAvailabilityData()
            }
            this.updateNowLine()
            this.scrollToNow()
          })
        }
      },
    }
    }
</script>

<style scoped lang="scss">
.v-event {
  &.availability-event {
    opacity: 0.9;
    border-left: 3px solid rgba(255, 255, 255, 0.8);
  }
  
  &.reservation-event {
    border-left: 2px solid rgba(255, 255, 255, 0.3);
  }
}

.availability-toggle {
  border: none !important;
  height: auto !important;
  .v-btn {
    height: 32px !important;
  }
}

// Availability event content styling
.availability-event-content {
  padding: 2px 4px;
  font-size: 11px;
  line-height: 1.2;
  
  .server-header {
    margin-bottom: 3px;
    
    strong {
      font-weight: 600;
      color: rgba(255, 255, 255, 0.95);
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
      font-size: 12px;
    }
  }
  
  .resource-list {
    .resource-item {
      display: flex;
      align-items: center;
      margin: 1px 0;
      
      .resource-indicator {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        margin-right: 3px;
        flex-shrink: 0;
        
        &.resource-high {
          background-color: #4CAF50;
        }
        
        &.resource-medium {
          background-color: #FF9800;
        }
        
        &.resource-low {
          background-color: #F44336;
        }
      }
      
      .resource-text {
        font-size: 10px;
        color: rgba(255, 255, 255, 0.9);
        text-shadow: 0 1px 1px rgba(0, 0, 0, 0.4);
        font-weight: 500;
      }
    }
  }
}

.calendar-sheet {
  position: relative;
}

.reservation-event-content {
  padding: 2px 4px;
  font-size: 11px;

  p {
    margin: 1px 0;
    color: rgba(255, 255, 255, 0.95);
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  }
}

.low-priority-label {
  font-size: 10px;
  font-style: italic;
  opacity: 0.85;
}
</style>

<style lang="scss">
// Calendar time slot interactivity
.v-calendar-daily__day-interval {
  cursor: pointer;

  &:hover {
    background-color: rgba(var(--v-theme-primary), 0.08);
  }
}

// Calendar event tooltip — dark background so white indicators/specs stay readable.
// Match Vuetify's own selector specificity (.v-tooltip > .v-overlay__content) and
// add our content-class so we win against the layered component rule.
.v-tooltip > .v-overlay__content.calendar-event-tooltip {
  background: rgba(30, 30, 30, 0.95) !important;
  color: rgba(255, 255, 255, 0.95) !important;
}

// "Now" indicator line — injected via JS into the calendar pane, so CSS must
// live in the non-scoped block to apply to a plain DOM element.
.now-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: #F44336;
  pointer-events: none;
  z-index: 3;
}

.now-line::before {
  content: '';
  position: absolute;
  left: -5px;
  top: -4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #F44336;
}

// Global styles for dynamically generated resource indicators
.resource-item {
  display: flex;
  align-items: center;
  margin: 1px 0;
  
  .resource-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 5px;
    flex-shrink: 0;
    display: inline-block;
    
    &.resource-high {
      background-color: #4CAF50 !important;
    }
    
    &.resource-medium {
      background-color: #FF9800 !important;
    }
    
    &.resource-low {
      background-color: #F44336 !important;
    }
  }
  
  .resource-text {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.9);
    text-shadow: 0 1px 1px rgba(0, 0, 0, 0.4);
    font-weight: 500;
  }
}
</style>