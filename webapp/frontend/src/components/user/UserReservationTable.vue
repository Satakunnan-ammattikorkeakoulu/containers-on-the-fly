<template>
  <div>
    <a v-if="hasLongItems" class="link-toggle-read-all" @click="toggleReadAll">{{ !readAll ? "Read all" : "Read less" }}</a>
    <v-data-table
      :headers="table.headers"
      :items="reservations"
      :sort-by="'createdAt'"
      :sort-desc="true"
      class="elevation-1">
      <!-- Status -->
      <template v-slot:item.status="{item}">
        <v-chip :color="getStatusColor(item.status)">{{item.status}}</v-chip>
      </template>
      <!-- Reserve date -->
      <template v-slot:item.createdAt="{item}">
        {{ parseTime(item.createdAt) }}
      </template>
      <!-- Start date -->
      <template v-slot:item.startDate="{item}">
        {{ parseTime(item.startDate) }}
      </template>
      <!-- End date -->
      <template v-slot:item.endDate="{item}">
        {{ parseTime(item.endDate) }}
      </template>
      <!-- Resources -->
      <template v-slot:item.resources="{item}">
        {{ getResources(item.reservedHardwareSpecs) }}
      </template>
      <!-- Container Image -->
      <template v-slot:item.containerImage="{item}">
        {{ item.reservedContainer.container.imageName }}
      </template>
      <!-- Ports -->
      <template v-slot:item.ports="{item}">
        <div v-html="getPorts(item.reservedContainer.reservedPorts)"></div>
      </template>
      <!-- Container Status -->
      <template v-slot:item.containerStatus="{item}">
        {{ item.status == "error" && item.reservedContainer.containerDockerErrorMessage ? getText(item.reservedContainer.containerDockerErrorMessage) : item.reservedContainer.containerStatus }}
      </template>
      <!-- Actions -->
      <template v-slot:item.actions="{item}">
        <a class="link-action" v-if="item.status == 'reserved' || item.status == 'started'" @click="emitCancelReservation(item.reservationId)">Cancel Reservation</a>
        <a class="link-action" v-if="item.status == 'started' && lessHoursThan(new Date(item.endDate), 24)" @click="emitExtendReservation(item.reservationId)">Extend Reservation</a>
        <a class="link-action" v-if="item.status == 'started'" @click="emitRestartContainer(item.reservationId)">Restart Container</a>
        <a class="link-action" v-if="item.status == 'started'" @click="emitShowReservationDetails(item.reservationId)">Show Details</a>
      </template>
    </v-data-table>
  </div>
</template>

<script>
  import { DisplayTime } from '/src/helpers/time.js'

  export default {
    name: 'UserReservationTable',
    props: {
      propReservations: {
        type: Array,
        required: true,
      }
    },
    data: () => ({
      reservations: [],
      cancellingReservation: false,
      readAll: false,
      hasLongItems: false,
      table: {
        headers: [
          {
            text: 'Status',
            align: 'start',
            sortable: false,
            value: 'status',
          },
          { text: 'Reserved', value: 'createdAt' },
          { text: 'Starts', value: 'startDate' },
          { text: 'Ends', value: 'endDate' },
          { text: 'Resources', value: 'resources' },
          { text: 'Container Image', value: 'containerImage' },
          { text: 'Ports', value: 'ports' },
          { text: 'Container Status', value: 'containerStatus' },
          { text: 'actions', value: 'actions' },
        ],
      }
    }),
    mounted () {
      this.reservations = this.propReservations
    },
    methods: {
      // Returns a string of all ports for a reservation
      getPorts(ports) {
        if (ports) {
          let portsString = ""
          for (let i = 0; i < ports.length; i++) {
            portsString += ports[i].localPort + " -> " + ports[i].outsidePort + " (" + ports[i].serviceName + ")"
            portsString += i != ports.length - 1 ? "<br />" : ""
          }
          return portsString
        }
        return ""
      },
      // Checks if the given time is between the given time + hours
      lessHoursThan(time, hours) {
        let curDate = new Date()
        let afterUtc = new Date(time.getTime() - (time.getTimezoneOffset() * 60000))
        
        let diff = afterUtc.getTime() - curDate.getTime()
        let diffHours = Math.ceil(diff / (1000 * 60 * 60))
        if (diffHours < 0) return false
        return diffHours <= hours
      },
      toggleReadAll() {
        this.readAll = !this.readAll;
      },
      getText(text) {
        if (this.readAll) return text;
        else {
          if (!this.hasLongItems) this.hasLongItems = true;
          return text.slice(0,10) + "...";
        }
      },
      emitExtendReservation(reservationId) {
        this.$emit('emitExtendReservation', reservationId)
      },
      emitCancelReservation(reservationId) {
        this.$emit('emitCancelReservation', reservationId)
      },
      emitRestartContainer(reservationId) {
        this.$emit('emitRestartContainer', reservationId)
      },
      emitShowReservationDetails(reservationId) {
        this.$emit('emitShowReservationDetails', reservationId)
      },
      getStatusColor(status) {
        if (status == "reserved") return "primary"
        else if (status == "started") return "green"
        else if (status == "stopped") return "red"
      },
      parseTime(timestamp) {
        return DisplayTime(timestamp)
      },
      getResources(specs) {
        if (specs) {
          let resources = ""
          for (let i = 0; i < specs.length; i++) {
            resources += specs[i].amount + " " + specs[i].format
            if (i != specs.length - 1) resources += ", "
          }
          return resources
        }
        return ""
      }
    },
    watch: {
      propReservations: {
        handler(newVal) {
          this.reservations = newVal
        },
        immediate: true,
      },
    },
  }
</script>

<style scoped lang="scss">
  .link-action {
    display: block;
    min-width: 150px;
    margin: 10px 0px;
  }

  .link-toggle-read-all {
    margin-bottom: 20px;
    font-size: 14px;
    display: inline-block;
    padding-left: 15px;
    width: auto;
  }
</style>