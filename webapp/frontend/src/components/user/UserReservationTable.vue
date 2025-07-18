<template>
  <div>
    <a v-if="hasLongItems" class="link-toggle-read-all" @click="toggleReadAll">{{ !readAll ? "Expand Issues" : "Collapse Issues" }}</a>
    <v-data-table
      :headers="table.headers"
      :items="reservations"
      :sort-by="'reservationId'"
      :sort-desc="true"
      class="elevation-1">
      <!-- Status -->
      <template v-slot:item.status="{item}">
        <v-chip :color="getStatusColor(item.status)">{{item.status}}</v-chip>
      </template>
      <!-- ID -->
      <template v-slot:item.reservationId="{item}">
        #{{ item.reservationId }}
      </template>
      <!-- Start date -->
      <template v-slot:item.startDate="{item}">
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <span v-bind="attrs" v-on="on" class="resource-link">{{ parseTime(item.startDate) }}</span>
          </template>
          <span>Reserved: {{ parseTime(item.createdAt) }}</span>
        </v-tooltip>
      </template>
      <!-- End date -->
      <template v-slot:item.endDate="{item}">
        {{ parseTime(item.endDate) }}
      </template>
      <!-- Resources -->
      <template v-slot:item.resourcesInfo="{item}">
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <span v-bind="attrs" v-on="on" class="resource-link">{{ item.computerName }}</span>
          </template>
          <div style="max-width: 300px;">
            <div><strong>Server:</strong> {{ item.computerName }}</div>
            <div><strong>Resources:</strong> {{ getResources(item.reservedHardwareSpecs) }}</div>
            <div><strong>Container:</strong> {{ item.reservedContainer.container.imageName }}</div>
            <div v-if="item.reservedContainer.reservedPorts && item.reservedContainer.reservedPorts.length > 0">
              <strong>Ports:</strong><br>
              <span v-html="getPorts(item.reservedContainer.reservedPorts)"></span>
            </div>
          </div>
        </v-tooltip>
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
          { text: 'ID', value: 'reservationId' },
          { text: 'Starts', value: 'startDate' },
          { text: 'Ends', value: 'endDate' },
          { text: 'Resources', value: 'resourcesInfo' },
          { text: 'Issues', value: 'containerStatus' },
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
            portsString += ports[i].localPort + " → " + ports[i].outsidePort + " (" + ports[i].serviceName + ")"
            portsString += i != ports.length - 1 ? "<br />" : ""
          }
          return portsString
        }
        return "No ports"
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
  
  .resource-link {
    cursor: help;
    text-decoration: underline;
    text-decoration-style: dotted;
  }
</style>