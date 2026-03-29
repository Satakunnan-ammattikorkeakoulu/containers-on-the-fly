<template>
  <div>
    <a v-if="hasLongItems" class="link-toggle-read-all" @click="toggleReadAll">{{ !readAll ? "Expand Issues" : "Collapse Issues" }}</a>
    <v-data-table
      :headers="table.headers"
      :items="reservations"
      :sort-by="[{key: 'reservationId', order: 'desc'}]"
      class="elevation-1">
      <!-- Status -->
      <template v-slot:item.status="{item}">
        <v-chip :color="getStatusColor(item.status)">{{item.status}}</v-chip>
      </template>
      <!-- ID -->
      <template v-slot:item.reservationId="{item}">
        #{{ item.reservationId }}
      </template>
      <!-- User -->
      <template v-slot:item.userEmail="{item}">
        {{ item.userEmail }} <small>(id: {{ item.userId }})</small>
      </template>
      <!-- Start date -->
      <template v-slot:item.startDate="{item}">
        <v-tooltip bottom>
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="resource-link">{{ parseTime(item.startDate) }}</span>
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
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="resource-link">{{ item.computerName }}</span>
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
      <!-- Docker Name -->
      <template v-slot:item.dockerName="{item}">
        {{ item.reservedContainer.containerDockerName }}
      </template>
      <!-- Container Status -->
      <template v-slot:item.containerStatus="{item}">
        {{ item.status == "error" && item.reservedContainer.containerDockerErrorMessage ? getText(item.reservedContainer.containerDockerErrorMessage) : item.reservedContainer.containerStatus }}
      </template>
      <!-- Actions -->
      <template v-slot:item.actions="{item}">
        <a class="link-action" v-if="item.status == 'reserved' || item.status == 'started'" @click="emitCancelReservation(item.reservationId)">Cancel Reservation</a>
        <a class="link-action" v-if="item.status == 'reserved' || item.status == 'started'" @click="emitChangeEndDate(item.reservationId)">Change End Date</a>
        <a class="link-action" v-if="item.status == 'started'" @click="emitRestartContainer(item.reservationId)">Restart Container</a>
        <a class="link-action" v-if="item.status == 'started'" @click="emitShowReservationDetails(item.reservationId)">Show Details</a>
      </template>
    </v-data-table>
  </div>
</template>

<script>
  import { DisplayTime } from '/src/helpers/time.js'

  export default {
    name: 'AdminReservationTable',
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
            title: 'Status',
            align: 'start',
            sortable: false,
            key: 'status',
          },
          { title: 'ID', key: 'reservationId' },
          { title: 'User', key: 'userEmail' },
          { title: 'Starts', key: 'startDate' },
          { title: 'Ends', key: 'endDate' },
          { title: 'Resources', key: 'resourcesInfo' },
          { title: 'Docker Name', key: 'dockerName' },
          { title: 'Issues', key: 'containerStatus' },
          { title: 'actions', key: 'actions' },
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
      emitChangeEndDate(reservationId) {
        this.$emit('emitChangeEndDate', reservationId)
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

  // Deep selector for tooltip styling
  :deep(.v-tooltip__content) {
    opacity: 1 !important;
    background-color: rgba(55, 61, 63, 0.95) !important;
    border: 1px solid #ddd;
  }
</style>