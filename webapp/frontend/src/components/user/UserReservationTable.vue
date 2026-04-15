<template>
  <div>
    <v-data-table-server
      :headers="table.headers"
      :items="propReservations"
      :items-length="totalItems"
      :loading="loading"
      :sort-by="sortBy"
      :items-per-page="itemsPerPage"
      :items-per-page-options="[10, 25, 50]"
      :page="page"
      @update:options="onOptionsUpdate"
      class="elevation-1">
      <!-- Status -->
      <template v-slot:item.status="{item}">
        <v-chip :color="getStatusColor(item.status)">{{ getStatusLabel(item.status) }}</v-chip>
        <v-tooltip bottom v-if="item.isLowPriority">
          <template v-slot:activator="{ props }">
            <v-chip v-bind="props" size="x-small" color="warning" style="margin-left: 4px;">Low Priority</v-chip>
          </template>
          <div style="max-width: 250px;">
            <strong>Low Priority</strong><br>
            This container may be paused if resources are needed by other reservations.
            It will automatically resume when resources become available.
            Save your work to mounted volumes to prevent data loss.
          </div>
        </v-tooltip>
      </template>
      <!-- ID -->
      <template v-slot:item.reservationId="{item}">
        #{{ item.reservationId }}
      </template>
      <!-- Description -->
      <template v-slot:item.description="{item}">
        <span v-if="item.description && item.description.trim()">
          <v-tooltip bottom v-if="item.description.length > 20">
            <template v-slot:activator="{ props }">
              <span v-bind="props" class="description-text">{{ truncateDescription(item.description) }}</span>
            </template>
            <span>{{ item.description }}</span>
          </v-tooltip>
          <span v-else class="description-text">{{ item.description }}</span>
        </span>
        <span v-else class="description-empty"></span>
      </template>
      <!-- Start date -->
      <template v-slot:item.startDate="{item}">
        <v-tooltip location="bottom">
          <template v-slot:activator="{ props }">
            <span v-bind="props">{{ parseRelativeTime(item.startDate) }}</span>
          </template>
          <div>{{ parseTime(item.startDate) }}</div>
          <div>Reserved: {{ parseTime(item.createdAt) }}</div>
        </v-tooltip>
      </template>
      <!-- End date -->
      <template v-slot:item.endDate="{item}">
        <v-tooltip location="bottom" :text="parseTime(item.endDate)">
          <template v-slot:activator="{ props }">
            <span v-bind="props">{{ parseRelativeTime(item.endDate) }}</span>
          </template>
        </v-tooltip>
      </template>
      <!-- Resources -->
      <template v-slot:item.resourcesInfo="{item}">
        <v-tooltip bottom>
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="link-hint">{{ item.computerName }}</span>
          </template>
          <div style="max-width: 300px;">
            <div><strong>Server:</strong> {{ item.computerName }}</div>
            <div><strong>Resources:</strong> {{ getResources(item.reservedHardwareSpecs) }}</div>
            <div><strong>SHM Size:</strong> {{ item.shmSizePercent || 50 }}% of RAM</div>
            <div v-if="item.ramDiskSizePercent && item.ramDiskSizePercent > 0"><strong>RAM Disk:</strong> {{ item.ramDiskSizePercent }}% of RAM</div>
            <div v-if="item.isLowPriority" style="color: #ff9800; font-weight: 500;">Low-Priority</div>
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
        <span v-if="(item.status == 'error' || item.status == 'restart_error') && item.reservedContainer.containerDockerErrorMessage">
          <span v-if="!readAll">{{ item.reservedContainer.containerDockerErrorMessage.slice(0, 10) }}...
            <a class="issue-action" @click="readAll = true">Expand</a>
          </span>
          <span v-else>{{ item.reservedContainer.containerDockerErrorMessage }}
            <a class="issue-action" @click="copyIssueText(item.reservedContainer.containerDockerErrorMessage)">Copy</a>
            <a class="issue-action" @click="readAll = false">Collapse</a>
          </span>
        </span>
      </template>
      <!-- Details link -->
      <template v-slot:item.details="{item}">
        <a v-if="item.status === 'started'" @click="emitShowReservationDetails(item.reservationId)">
          Show Details
        </a>
      </template>
      <!-- Actions -->
      <template v-slot:item.actions="{item}">
        <v-menu v-if="item.status === 'reserved' || item.status === 'started' || item.status === 'restart_error' || item.status === 'paused'">
          <template v-slot:activator="{ props }">
            <a v-bind="props">
              Actions <v-icon size="small">mdi-chevron-down</v-icon>
            </a>
          </template>
          <v-list density="compact">
            <v-list-item v-if="item.status === 'started' && lessHoursThan(new Date(item.endDate), 24)" @click="emitExtendReservation(item.reservationId)">
              <template v-slot:prepend><v-icon size="small">mdi-clock-plus-outline</v-icon></template>
              <v-list-item-title>Extend Reservation</v-list-item-title>
            </v-list-item>
            <v-list-item @click="emitEditDescription(item.reservationId, item.description)">
              <template v-slot:prepend><v-icon size="small">mdi-pencil-outline</v-icon></template>
              <v-list-item-title>Edit Description</v-list-item-title>
            </v-list-item>
            <v-list-item v-if="item.status === 'started' || item.status === 'restart_error'" @click="emitRestartContainer(item.reservationId)">
              <template v-slot:prepend><v-icon size="small">mdi-restart</v-icon></template>
              <v-list-item-title>Restart Container</v-list-item-title>
            </v-list-item>
            <v-divider class="my-1" />
            <v-list-item @click="emitCancelReservation(item.reservationId)" class="cancel-action">
              <template v-slot:prepend><v-icon size="small">mdi-cancel</v-icon></template>
              <v-list-item-title>Cancel Reservation</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </template>
    </v-data-table-server>
  </div>
</template>

<script>
  /**
   * Server-side paginated data table listing the current user's reservations
   * with status chips, resource tooltips, and an actions menu for show-details,
   * extend, restart, edit description, and cancel operations.
   * Emits pagination/sort changes and row actions to the parent.
   */
  import { DisplayTime, RelativeTime } from '/src/helpers/time.js'
  import { useMainStore } from '/src/store/store.js'
  import { copyToClipboard } from '/src/helpers/clipboard.js'

  export default {
    name: 'UserReservationTable',
    setup() {
      const store = useMainStore()
      return { store }
    },
    props: {
      propReservations: {
        type: Array,
        required: true,
      },
      totalItems: {
        type: Number,
        default: 0,
      },
      loading: {
        type: Boolean,
        default: false,
      },
      page: {
        type: Number,
        default: 1,
      },
      itemsPerPage: {
        type: Number,
        default: 10,
      },
      sortBy: {
        type: Array,
        default: () => [{key: 'reservationId', order: 'desc'}],
      },
    },
    data: () => ({
      cancellingReservation: false,
      readAll: false,
      table: {
        headers: [
          {
            title: 'Status',
            align: 'start',
            sortable: false,
            key: 'status',
          },
          { title: 'ID', key: 'reservationId' },
          { title: 'Starts', key: 'startDate' },
          { title: 'Ends', key: 'endDate' },
          { title: 'Resources', key: 'resourcesInfo', sortable: false },
          { title: 'Description', key: 'description', sortable: false },
          { title: 'Issues', key: 'containerStatus', sortable: false },
          { title: '', key: 'details', sortable: false },
          { title: '', key: 'actions', sortable: false },
        ],
      }
    }),
    methods: {
      truncateDescription(description) {
        if (!description) return "-";
        return description.length > 20 ? description.substring(0, 20) + "..." : description;
      },
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
      lessHoursThan(time, hours) {
        let curDate = new Date()
        let afterUtc = new Date(time.getTime() - (time.getTimezoneOffset() * 60000))

        let diff = afterUtc.getTime() - curDate.getTime()
        let diffHours = Math.ceil(diff / (1000 * 60 * 60))
        if (diffHours < 0) return false
        return diffHours <= hours
      },
      copyIssueText(text) {
        if (!text) return;
        copyToClipboard(text).then(ok => {
          this.store.showMessage({ text: ok ? "Issue text copied to clipboard" : "Failed to copy to clipboard", color: ok ? "green" : "red" });
        });
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
      emitEditDescription(reservationId, currentDescription) {
        this.$emit('emitEditDescription', reservationId, currentDescription)
      },
      getStatusLabel(status) {
        const labels = {
          "reserved": "Reserved",
          "started": "Running",
          "stopping": "Stopping",
          "stopped": "Stopped",
          "error": "Startup Error",
          "restart_error": "Error Restarting",
          "restart": "Restarting",
          "paused": "Paused",
        }
        return labels[status] || status
      },
      getStatusColor(status) {
        if (status == "reserved") return "primary"
        else if (status == "started") return "green"
        else if (status == "stopping") return "orange"
        else if (status == "stopped") return "red"
        else if (status == "restart_error") return "orange"
        else if (status == "paused") return "warning"
      },
      parseTime(timestamp) {
        return DisplayTime(timestamp)
      },
      parseRelativeTime(timestamp) {
        if (!timestamp) return '-'
        return RelativeTime(timestamp)
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
      },
      onOptionsUpdate(options) {
        this.$emit('update:options', options)
      },
    },
  }
</script>

<style scoped lang="scss">
  .issue-action {
    font-size: 12px;
    margin-left: 4px;
  }

  .description-text {
    font-size: 13px;
  }

  .description-empty {
    color: #999;
  }

  .cancel-action .v-list-item-title,
  .cancel-action .v-icon {
    color: #ef5350;
  }
</style>
