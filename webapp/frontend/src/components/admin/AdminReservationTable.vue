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
        <v-tooltip
          v-if="(item.status === 'error' || item.status === 'restart_error') && item.reservedContainer.containerDockerErrorMessage"
          location="top"
          max-width="400"
        >
          <template v-slot:activator="{ props }">
            <v-chip
              v-bind="props"
              :color="getStatusColor(item.status)"
              variant="tonal"
              prepend-icon="mdi-alert-circle"
              class="link-hint"
              style="cursor: pointer;"
              @click="copyIssueText(item.reservedContainer.containerDockerErrorMessage)"
            >{{ getStatusLabel(item.status) }}</v-chip>
          </template>
          <div style="white-space: pre-wrap;">{{ item.reservedContainer.containerDockerErrorMessage }}</div>
          <div class="mt-3 text-caption" style="font-weight: bold;">Click to copy</div>
        </v-tooltip>
        <v-chip v-else :color="getStatusColor(item.status)" variant="tonal">{{ getStatusLabel(item.status) }}</v-chip>
      </template>
      <!-- ID -->
      <template v-slot:item.reservationId="{item}">
        #{{ item.reservationId }}
      </template>
      <!-- User (clickable to filter) -->
      <template v-slot:item.userEmail="{item}">
        <v-tooltip location="bottom" text="Click to filter by this user">
          <template v-slot:activator="{ props }">
            <span v-bind="props" class="link-hint" @click="$emit('filterByUser', item.userEmail)">
              {{ item.userEmail }}<span v-if="item.userName"> ({{ item.userName }})</span>
            </span>
          </template>
        </v-tooltip>
        <small>(id: {{ item.userId }})</small>
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
        <div class="d-flex align-center" style="gap: 8px;">
          <v-tooltip bottom>
            <template v-slot:activator="{ props }">
              <span v-bind="props" class="link-hint" style="cursor: pointer;" @click="copyResourcesInfo(item)">{{ item.computerName }}</span>
            </template>
            <div style="max-width: 300px;">
              <div><strong>Server:</strong> {{ item.computerName }}</div>
              <div><strong>Resources:</strong> {{ getResources(item.reservedHardwareSpecs) }}</div>
              <div><strong>SHM Size:</strong> {{ item.shmSizePercent || 50 }}% of RAM</div>
              <div v-if="item.ramDiskSizePercent && item.ramDiskSizePercent > 0"><strong>RAM Disk:</strong> {{ item.ramDiskSizePercent }}% of RAM</div>
              <div><strong>Container:</strong> {{ item.reservedContainer.container.imageName }}</div>
              <div v-if="item.reservedContainer.containerDockerName"><strong>Container Name:</strong> {{ item.reservedContainer.containerDockerName }}</div>
              <div v-if="item.reservedContainer.containerDockerId"><strong>Docker ID:</strong> {{ item.reservedContainer.containerDockerId }}</div>
              <div v-if="item.reservedContainer.reservedPorts && item.reservedContainer.reservedPorts.length > 0">
                <strong>Ports:</strong><br>
                <span v-html="getPorts(item.reservedContainer.reservedPorts)"></span>
                <div v-if="item.status === 'paused'" class="text-caption mt-1" style="font-style: italic;">
                  Ports held for resume &mdash; may change if the server runs out of ports.
                </div>
              </div>
              <div class="mt-3 text-caption" style="font-weight: bold;">Click to copy</div>
            </div>
          </v-tooltip>
          <v-tooltip v-if="item.isLowPriority" bottom max-width="280">
            <template v-slot:activator="{ props }">
              <v-chip
                v-bind="props"
                size="x-small"
                color="grey"
                variant="tonal"
                prepend-icon="mdi-chevron-double-down"
                class="ml-2"
              >Low Priority</v-chip>
            </template>
            <div>
              <strong>Low Priority</strong><br>
              This container may be paused if resources are needed by other reservations, and will automatically resume when resources become available.
              When paused, the container is recreated &mdash; only files on mounted volumes persist.
              Outside ports are held and normally restored on resume.
            </div>
          </v-tooltip>
          <span v-if="item.description && item.description.trim()" class="text-medium-emphasis" style="font-size: 12px; font-style: italic;">&ldquo;{{ item.description }}&rdquo;</span>
        </div>
      </template>
      <!-- Actions (Show Details + menu) -->
      <template v-slot:item.actions="{item}">
        <div class="d-flex justify-end align-center" style="padding-right: 15px;">
          <a v-if="item.status === 'started'" class="mr-8" @click="emitShowReservationDetails(item.reservationId)">
            <v-icon size="small" class="mr-1">mdi-eye-outline</v-icon>Show Details
          </a>
          <v-menu v-if="item.status === 'reserved' || item.status === 'started' || item.status === 'restart_error' || item.status === 'paused'">
            <template v-slot:activator="{ props }">
              <a v-bind="props">
                <v-icon size="small" class="mr-1">mdi-cog-outline</v-icon>Actions <v-icon size="small">mdi-chevron-down</v-icon>
              </a>
            </template>
            <v-list density="compact">
              <v-list-item @click="emitChangeEndDate(item.reservationId, item.endDate)">
                <template v-slot:prepend><v-icon size="small">mdi-calendar-edit</v-icon></template>
                <v-list-item-title>Adjust End Date</v-list-item-title>
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
        </div>
      </template>
    </v-data-table-server>
  </div>
</template>

<script>
  /**
   * Server-side paginated data table of all reservations with status, user, dates,
   * resource summary (absorbing the Docker container name/id), and row actions.
   * Emits pagination/sort changes and row actions to the parent.
   * Used in PageAdminReservations.
   */
  import { DisplayTime, RelativeTime } from '/src/helpers/time.js'
  import { useMainStore } from '/src/store/store.js'
  import { copyToClipboard } from '/src/helpers/clipboard.js'

  export default {
    name: 'AdminReservationTable',
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
      table: {
        headers: [
          {
            title: 'Status',
            align: 'start',
            sortable: false,
            key: 'status',
            width: '180px',
          },
          { title: 'ID', key: 'reservationId', width: '100px' },
          { title: 'User', key: 'userEmail' },
          { title: 'Starts', key: 'startDate', width: '180px' },
          { title: 'Ends', key: 'endDate', width: '180px' },
          { title: 'Resources', key: 'resourcesInfo', sortable: false },
          { title: '', key: 'actions', sortable: false, align: 'end' },
        ],
      }
    }),
    methods: {
      /** Returns an HTML string listing all port mappings (local -> outside) for a reservation tooltip. */
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
      copyIssueText(text) {
        if (!text) return;
        copyToClipboard(text).then(ok => {
          this.store.showMessage({ text: ok ? "Issue text copied to clipboard" : "Failed to copy to clipboard", color: ok ? "green" : "red" });
        });
      },
      copyResourcesInfo(item) {
        const lines = [
          `Server: ${item.computerName}`,
          `Resources: ${this.getResources(item.reservedHardwareSpecs)}`,
          `SHM Size: ${item.shmSizePercent || 50}% of RAM`,
        ];
        if (item.ramDiskSizePercent && item.ramDiskSizePercent > 0) {
          lines.push(`RAM Disk: ${item.ramDiskSizePercent}% of RAM`);
        }
        if (item.isLowPriority) {
          lines.push("Low-Priority");
        }
        lines.push(`Container: ${item.reservedContainer.container.imageName}`);
        if (item.reservedContainer.containerDockerName) {
          lines.push(`Container Name: ${item.reservedContainer.containerDockerName}`);
        }
        if (item.reservedContainer.containerDockerId) {
          lines.push(`Docker ID: ${item.reservedContainer.containerDockerId}`);
        }
        if (item.reservedContainer.reservedPorts && item.reservedContainer.reservedPorts.length > 0) {
          lines.push("Ports:");
          for (const port of item.reservedContainer.reservedPorts) {
            lines.push(`  ${port.localPort} → ${port.outsidePort} (${port.serviceName})`);
          }
        }
        const text = lines.join("\n");
        copyToClipboard(text).then(ok => {
          this.store.showMessage({ text: ok ? "Resources info copied to clipboard" : "Failed to copy to clipboard", color: ok ? "green" : "red" });
        });
      },
      emitCancelReservation(reservationId) {
        this.$emit('emitCancelReservation', reservationId)
      },
      emitChangeEndDate(reservationId, endDate) {
        this.$emit('emitChangeEndDate', reservationId, endDate)
      },
      emitRestartContainer(reservationId) {
        this.$emit('emitRestartContainer', reservationId)
      },
      emitShowReservationDetails(reservationId) {
        this.$emit('emitShowReservationDetails', reservationId)
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
        else if (status == "stopping") return "grey"
        else if (status == "stopped") return "grey"
        else if (status == "error") return "red"
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
      /** Formats reserved hardware specs into a comma-separated summary string (e.g. "4 vCPUs, 16 GB RAM"). */
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
  .cancel-action .v-list-item-title,
  .cancel-action .v-icon {
    color: #ef5350;
  }

  // Deep selector for tooltip styling
  :deep(.v-tooltip__content) {
    opacity: 1 !important;
    background-color: rgba(55, 61, 63, 0.95) !important;
    border: 1px solid #ddd;
  }
</style>
