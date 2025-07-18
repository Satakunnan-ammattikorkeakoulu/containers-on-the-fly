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
          <v-spacer></v-spacer>
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
            <p><b>{{event.eventParsed.input.name}}</b></p>
            <p v-html="getReservationSpecs(event.eventParsed.input.reservationId)" />
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
      colors: ['red', 'pink', 'purple', 'deep-purple', 'indigo', 'blue',
               'light-blue', 'cyan', 'teal', 'green', 'light-green darken-1',
               'lime darken-2', 'yellow darken-3', 'amber darken-2', 'orange darken-3', 'deep-orange', 'brown', 'grey', 'blue-grey'],
    }),
    mounted () {
      this.$refs.calendar.checkChange()
    },
    methods: {
      intervalFormat(interval) {
        return interval.time
      },
      selectSlot( event ) {
        // If calendar is in read-only mode, don't allow slot selection
        if (this.readOnly) {
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
    },
    watch: {
      propReservations: {
        immediate: true,
        handler (newVal) {
          //console.log(newVal)
          let events = []
          newVal.forEach((res) => {
            let color = this.colors[this.rnd(0, this.colors.length - 1)]
            events.push({
              name: "Reservation #" + res.reservationId,
              reservationId: res.reservationId,
              // res.startDate in format: 2022-04-29T02:00:00
              start: dayjs(TimestampToLocalTimeZone(res.startDate)).toDate(),
              end: dayjs(TimestampToLocalTimeZone(res.endDate)).toDate(),
              color: color,
              timed: true,
            })
          })
          this.events = events
        }
      }
    }
    }
</script>

<style scoped lang="scss">
</style>