<template>
  <v-row class="fill-height">
    <v-col>
      <v-sheet height="64">
        <v-toolbar flat>
          <v-btn outlined class="mr-4" color="grey darken-2" @click="setToday">
            Today
          </v-btn>
          <v-btn fab text small color="grey darken-2" @click="prev">
            <v-icon small>
              mdi-chevron-left
            </v-icon>
          </v-btn>
          <v-btn fab text small color="grey darken-2" @click="next">
            <v-icon small>
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
          >
            <v-btn small value="reservations">
              <v-icon small>mdi-calendar-clock</v-icon>
              Reservations
            </v-btn>
            <v-btn small value="availability">
              <v-icon small>mdi-server</v-icon>
              Availability
            </v-btn>
          </v-btn-toggle>
          <v-btn
            small
            outlined
            class="ma-2"
            @click="refreshCalendarData"
          >
            <v-icon small left>mdi-refresh</v-icon>
            Refresh
          </v-btn>
          <v-spacer></v-spacer>
          <v-toolbar-title v-if="$refs.calendar">
            {{ $refs.calendar.title }}
          </v-toolbar-title>
        </v-toolbar>
      </v-sheet>
      <v-sheet height="600">
        <v-calendar
          ref="calendar"
          v-model="focus"
          color="primary"
          :events="events"
          :event-color="getEventColor"
          :type="type"
          :weekdays="weekdays"
          @mouseup:time="selectSlot"
          event-overlap-mode="column"
          first-interval="0"
          interval-minutes="30"
          interval-count="48"
          :interval-format="intervalFormat"
        >
          <template #event="event">
            <div v-if="event.eventParsed.input.type === 'availability'" class="availability-event-content">
              <div class="server-header">
                <strong>{{event.eventParsed.input.computerName}}</strong>
              </div>
              <div class="resource-list" v-html="formatResourcesWithIndicators(event.eventParsed.input)" />
            </div>
            <div v-else class="reservation-event-content">
              <p><b>{{event.eventParsed.input.name}}</b></p>
              <p v-html="getReservationSpecs(event.eventParsed.input.reservationId)" />
            </div>
          </template>
        </v-calendar>
        <v-menu v-model="selectedOpen" :close-on-content-click="false" :activator="selectedElement" offset-x>
          <v-card color="grey lighten-4" min-width="350px" flat>
            <v-toolbar :color="selectedEvent.color" dark>
              <v-btn icon>
                <v-icon>mdi-pencil</v-icon>
              </v-btn>
              <v-toolbar-title v-html="selectedEvent.name"></v-toolbar-title>
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
              <v-btn text color="secondary" @click="selectedOpen = false">
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
  import { TimestampToLocalTimeZone } from '/src/helpers/time.js'
  import dayjs from "dayjs";
  const axios = require('axios').default;
  var utc = require('dayjs/plugin/utc')
  var timezone = require('dayjs/plugin/timezone')
  dayjs.extend(utc)
  var customParseFormat = require('dayjs/plugin/customParseFormat')
  dayjs.extend(timezone)
  dayjs.extend(customParseFormat)

  export default {
    name: 'CalendarReservations',
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
    }),
    mounted () {
      if (this.$refs.calendar) {
        this.$refs.calendar.checkChange()
      }
    },
    methods: {
      intervalFormat(interval) {
        return interval.time
      },
      selectSlot( event ) {
        // If calendar is in read-only mode or availability mode, don't allow slot selection
        if (this.readOnly || this.viewMode === 'availability') {
          return
        }
        
        let now = dayjs()
        let selectedTime = dayjs(event.date + " " + event.time)
        // Round to nearest 30 minutes (down)
        if (selectedTime.get("minutes") < 30)
          selectedTime = selectedTime.set("minute", 0)
        else
          selectedTime = selectedTime.set("minute", 30)
        
        // Check that reservation is not made into past
        if (selectedTime < now) {
          this.$store.commit('showMessage', { text: "Can only make reservations into future.", color: "red" })
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
      formatResourcesWithIndicators(availabilityEvent) {
        if (!availabilityEvent.availableSpecs) {
          return availabilityEvent.resourceText
        }
        
        let html = ''
        const specs = availabilityEvent.availableSpecs
        
        Object.values(specs).forEach(spec => {
          // Calculate availability ratio for this specific resource
          const ratio = spec.available / Math.max(spec.maximum, 1)
          let indicatorClass = 'resource-low'
          if (ratio > 0.75) indicatorClass = 'resource-high'
          else if (ratio > 0.25) indicatorClass = 'resource-medium'
          
          let displayText = ''
          if (spec.type.toLowerCase() === 'gpu' || spec.type.toLowerCase() === 'gpus') {
            displayText = `GPU: ${Math.round(spec.available)}/${Math.round(spec.maximum)}`
          } else if (spec.type.toLowerCase() === 'cpu' || spec.type.toLowerCase() === 'cpus') {
            displayText = `CPU: ${Math.round(spec.available)}/${Math.round(spec.maximum)}`
          } else if (spec.type.toLowerCase() === 'ram') {
            displayText = `RAM: ${Math.round(spec.available)}/${Math.round(spec.maximum)} ${spec.format}`
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
            calendarStart = focusDate.startOf('week');
            calendarEnd = focusDate.endOf('week').add(1, 'day');
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
            headers: {"Authorization" : `Bearer ${this.$store.state.user.loginToken}`},
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
          this.$store.commit('showMessage', { text: "Error loading availability data.", color: "red" })
        }
      },
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
            calendarStart = focusDate.startOf('week');
            calendarEnd = focusDate.endOf('week').add(1, 'day');
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
            headers: {"Authorization" : `Bearer ${this.$store.state.user.loginToken}`},
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
          this.$store.commit('showMessage', { text: "Error refreshing reservations.", color: "red" })
        }
      },
      updateDisplayedEvents() {
        
        if (this.viewMode === 'availability') {
          this.events = this.availabilityEvents
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
              start: startDate.toDate(),
              end: endDate.toDate(),
              color: color,
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
  .v-btn--active {
    background-color: primary !important;
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

.reservation-event-content {
  padding: 2px 4px;
  font-size: 11px;
  
  p {
    margin: 1px 0;
    color: rgba(255, 255, 255, 0.95);
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  }
}
</style>

<style lang="scss">
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